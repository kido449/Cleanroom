import os
import sys
import json
import time
import datetime
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from pydantic import ValidationError

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from src.validation.validate import validate_extraction
from data.schema.schema import ExtractedDocument
from src.hitl.queue import add_to_review_queue

# Set up logging directory and handlers
logs_dir = project_root / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("extraction_pipeline")
logger.setLevel(logging.INFO)

if not logger.handlers:
    # Rotating file handler
    file_handler = RotatingFileHandler(
        filename=logs_dir / "extraction.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)


def _log_audit_telemetry(status: str, attempts: int, latency_ms: float, errors: List[List[str]], model_name: str, queue_id: Optional[str] = None):
    """Persist structured JSON audit telemetry for every extraction run."""
    telemetry_file = logs_dir / "audit_telemetry.jsonl"
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": status,
        "attempts": attempts,
        "latency_ms": round(latency_ms, 2),
        "error_count": len(errors),
        "model": model_name,
        "queue_id": queue_id
    }
    try:
        with open(telemetry_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write audit telemetry: {e}")


def _build_correction_prompt(raw_text: str, last_attempt_json: Any, errors: List[str]) -> str:
    """Build exact correction prompt instructing model to fix only failed Pydantic validation fields."""
    errors_str = "\n".join(f"- {err}" for err in errors)
    if isinstance(last_attempt_json, (dict, list)):
        invalid_json_str = json.dumps(last_attempt_json, indent=2)
    else:
        invalid_json_str = str(last_attempt_json)
        
    schema_json = json.dumps(ExtractedDocument.model_json_schema(), indent=2)

    return f"""You previously extracted structured JSON from a text, but the output failed Pydantic validation.

ORIGINAL TEXT:
{raw_text}

TARGET PYDANTIC SCHEMA STRUCTURE:
{schema_json}

INVALID JSON PRODUCED IN LAST ATTEMPT:
{invalid_json_str}

VALIDATION ERRORS ENCOUNTERED:
{errors_str}

INSTRUCTIONS:
Fix ONLY the fields mentioned in the errors above. Return the complete corrected JSON matching the schema precisely.
Return ONLY valid JSON without any markdown formatting or explanations.
"""


def extract_with_repair(
    raw_text: str,
    max_retries: int = 3,
    extractor: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Self-correcting extraction loop that calls an extractor, validates via ExtractedDocument,
    and re-prompts with explicit validation error feedback up to `max_retries` attempts.
    """
    if extractor is None:
        from src.extractor import GroqExtractor
        extractor = GroqExtractor()

    t0 = time.time()
    model_name = getattr(extractor, "model_name", "unknown_model")

    all_errors_encountered: List[List[str]] = []
    last_errors: List[str] = []
    last_attempt_json: Any = {}
    correction_prompt: Optional[str] = None

    for attempt in range(1, max_retries + 1):
        logger.info(f"Starting extraction attempt {attempt}/{max_retries}")

        try:
            # Call extractor
            if correction_prompt:
                if hasattr(extractor, "extract"):
                    try:
                        raw_result = extractor.extract(raw_text, prompt_override=correction_prompt)
                    except TypeError:
                        raw_result = extractor.extract(correction_prompt)
                elif hasattr(extractor, "extract_with_prompt"):
                    raw_result = extractor.extract_with_prompt(correction_prompt)
                else:
                    raw_result = extractor(correction_prompt)
            else:
                if hasattr(extractor, "extract"):
                    raw_result = extractor.extract(raw_text)
                else:
                    raw_result = extractor(raw_text)

            last_attempt_json = raw_result

            # Run through validate_extraction()
            is_valid, errors = validate_extraction(raw_result)
            if not is_valid:
                last_errors = errors
                all_errors_encountered.append(errors)
                if attempt < max_retries:
                    logger.warning(
                        f"Attempt {attempt}/{max_retries} failed validation. "
                        f"Errors: {errors}. Triggering self-correction retry..."
                    )
                    correction_prompt = _build_correction_prompt(raw_text, last_attempt_json, errors)
                    continue
                else:
                    logger.error(
                        f"Attempt {attempt}/{max_retries} failed validation after {max_retries} attempts. "
                        f"Last errors: {errors}. Flagging ticket for human review."
                    )
                    break
            else:
                logger.info(f"Attempt {attempt}/{max_retries} succeeded: validation passed.")
                _log_audit_telemetry("success", attempt, (time.time() - t0) * 1000, all_errors_encountered, model_name)
                return {
                    "status": "success",
                    "attempts": attempt,
                    "errors_encountered": all_errors_encountered,
                    "data": raw_result
                }

        except json.JSONDecodeError as e:
            # JSON parsing failure counts as validation/repair budget
            last_errors = [f"JSONDecodeError: {str(e)}"]
            all_errors_encountered.append(last_errors)
            last_attempt_json = {}
            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt}/{max_retries} failed with JSONDecodeError: {e}. "
                    f"Triggering self-correction retry..."
                )
                correction_prompt = _build_correction_prompt(raw_text, last_attempt_json, last_errors)
                continue
            else:
                logger.error(
                    f"Attempt {attempt}/{max_retries} failed with JSONDecodeError after {max_retries} attempts. "
                    f"Last errors: {last_errors}. Flagging ticket for human review."
                )
                break

        except ValidationError as e:
            # Pydantic validation error raised directly inside extractor
            errors = []
            for err in e.errors():
                loc_str = " -> ".join(str(item) for item in err["loc"])
                msg = err.get("msg", "Validation error")
                errors.append(f"{loc_str}: {msg}" if loc_str else msg)
            last_errors = errors
            all_errors_encountered.append(errors)
            last_attempt_json = getattr(e, "input", {})
            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt}/{max_retries} failed validation (ValidationError). "
                    f"Errors: {errors}. Triggering self-correction retry..."
                )
                correction_prompt = _build_correction_prompt(raw_text, last_attempt_json, errors)
                continue
            else:
                logger.error(
                    f"Attempt {attempt}/{max_retries} failed validation after {max_retries} attempts. "
                    f"Last errors: {errors}. Flagging ticket for human review."
                )
                break

        except Exception as e:
            # API-level failures (network errors, rate limits, timeouts) handled separately
            # They do NOT count against the max_retries validation-repair budget.
            logger.error(f"API/Network-level failure encountered during extraction on attempt {attempt}: {e}")
            raise e

    # If we exit the loop after max_retries without returning success
    queue_id = add_to_review_queue(raw_text, last_attempt_json, last_errors, max_retries)
    _log_audit_telemetry("flagged_for_review", max_retries, (time.time() - t0) * 1000, all_errors_encountered, model_name, queue_id=queue_id)
    return {
        "status": "flagged_for_review",
        "attempts": max_retries,
        "last_errors": last_errors,
        "raw_text": raw_text,
        "last_attempt_json": last_attempt_json,
        "queue_id": queue_id
    }
