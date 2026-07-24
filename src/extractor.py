import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from tenacity.wait import wait_base
from tenacity import RetryCallState
import re
import logging

logger = logging.getLogger("extractor")

# Ensure project root is in sys.path for relative imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import Config
from data.schema.schema import ExtractedDocument


class wait_groq_rate_limit(wait_base):
    """
    Custom tenacity wait strategy for Groq API 429 / RateLimitError.
    Parses retry-after header or error message for wait duration.
    Falls back to a configurable default wait (60s) if delay cannot be parsed.
    """
    def __init__(self, fallback_wait: float = 60.0):
        self.fallback_wait = fallback_wait
        self.exponential = wait_exponential(multiplier=1, min=2, max=10)

    def __call__(self, retry_state: RetryCallState) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if exc is not None:
            exc_str = str(exc)
            exc_type_name = type(exc).__name__

            is_429 = (
                "RateLimitError" in exc_type_name
                or "429" in exc_str
                or "rate_limit" in exc_str.lower()
                or "quota" in exc_str.lower()
                or "too many requests" in exc_str.lower()
            )

            if is_429:
                wait_seconds = None

                # 1. Check response headers for retry-after
                if hasattr(exc, "response") and exc.response is not None:
                    retry_after = getattr(exc.response, "headers", {}).get("retry-after")
                    if retry_after:
                        try:
                            wait_seconds = float(retry_after)
                        except (ValueError, TypeError):
                            pass

                # 2. Parse from error message string
                if wait_seconds is None:
                    match_s = re.search(r"[Pp]lease try again in ([0-9]+(?:\.[0-9]+)?)s", exc_str)
                    match_ms = re.search(r"[Pp]lease try again in ([0-9]+(?:\.[0-9]+)?)ms", exc_str)
                    match_m = re.search(r"[Pp]lease try again in ([0-9]+(?:\.[0-9]+)?)m", exc_str)
                    if match_s:
                        wait_seconds = float(match_s.group(1))
                    elif match_ms:
                        wait_seconds = float(match_ms.group(1)) / 1000.0
                    elif match_m:
                        wait_seconds = float(match_m.group(1)) * 60.0

                if wait_seconds is None or wait_seconds <= 0:
                    wait_seconds = self.fallback_wait

                wait_seconds = round(wait_seconds + 1.0, 2)

                if wait_seconds > 120.0:
                    msg = f"\n❌ Groq rate limit wait ({wait_seconds}s) exceeds 120s safety threshold. Raising immediately to prevent stall..."
                    print(msg, flush=True)
                    logger.error(f"Groq rate limit wait ({wait_seconds}s) > 120s. Raising exc.")
                    raise exc

                msg = f"\n⏳ Groq rate limited (HTTP 429). Waiting {wait_seconds}s before retry (attempt {retry_state.attempt_number})..."
                print(msg, flush=True)
                logger.warning(f"Groq rate limited (HTTP 429). Waiting {wait_seconds}s before retry.")
                return wait_seconds

        return self.exponential(retry_state)


class GroqExtractor:
    """Primary extraction engine using Groq Cloud API (llama-3.3-70b-versatile)."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        from groq import Groq
        api_key = api_key or Config.GROQ_API_KEY
        if not api_key:
            raise ValueError("GROQ_API_KEY is required but not found in environment or arguments.")
        self.client = Groq(api_key=api_key, timeout=45.0)
        self.model_name = model_name or Config.GROQ_MODEL
        self.schema_class = ExtractedDocument

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_groq_rate_limit(fallback_wait=60.0),
        reraise=True
    )
    def _generate_content_with_retry(self, prompt: str) -> str:
        """Call Groq API with tenacity retry logic for API/network errors."""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise data extraction assistant. You MUST return ONLY valid JSON. No markdown formatting, no explanations, no text before or after the JSON object."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        return response.choices[0].message.content

    def extract(self, text: str, prompt_override: Optional[str] = None) -> Dict[str, Any]:
        if prompt_override:
            prompt = prompt_override
        else:
            schema_json = json.dumps(self.schema_class.model_json_schema(), indent=2)
            prompt = f"""Extract structured JSON from the following text matching this exact Pydantic schema structure:

{schema_json}

TEXT TO EXTRACT:
{text}

Return ONLY valid JSON matching the schema structure exactly. Do not include explanations or markdown formatting outside of the JSON string."""

        raw_text = self._generate_content_with_retry(prompt)

        # Clean response string if model wrapped in markdown fences
        clean_text = raw_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        raw_json = json.loads(clean_text)

        # Validate with Pydantic model
        validated = self.schema_class.model_validate(raw_json)
        return validated.model_dump()
