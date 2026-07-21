import json
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import sys

# Ensure project root is in path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data.schema.schema import ExtractedDocument
from src.validation.validate import validate_extraction

HITL_QUEUE_FILE = project_root / "data" / "hitl_queue.jsonl"


def _ensure_queue_file():
    HITL_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not HITL_QUEUE_FILE.exists():
        HITL_QUEUE_FILE.touch(exist_ok=True)


def add_to_review_queue(
    raw_text: str,
    last_attempt_json: Any,
    last_errors: List[str],
    attempts_taken: int,
    ticket_id: Optional[str] = None
) -> str:
    """
    Add an unrepairable or flagged extraction result to the HITL review queue.
    Returns the assigned queue_item_id.
    """
    _ensure_queue_file()
    
    # Try to extract ticket_id from last_attempt_json or generate a unique ID
    if not ticket_id and isinstance(last_attempt_json, dict):
        ticket_id = last_attempt_json.get("ticket_id")
    if not ticket_id:
        ticket_id = f"HITL-{uuid.uuid4().hex[:8].upper()}"

    # Check if this ticket_id is already pending to avoid exact duplicates
    existing_pending = get_pending_reviews()
    for item in existing_pending:
        if item.get("ticket_id") == ticket_id and item.get("raw_text") == raw_text:
            return item.get("queue_id", ticket_id)

    queue_id = f"Q-{uuid.uuid4().hex[:8].upper()}"
    entry = {
        "queue_id": queue_id,
        "ticket_id": ticket_id,
        "status": "pending_review",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "attempts_taken": attempts_taken,
        "raw_text": raw_text,
        "last_attempt_json": last_attempt_json if isinstance(last_attempt_json, dict) else {},
        "last_errors": last_errors,
        "resolved_at": None,
        "resolved_json": None,
        "reviewer_notes": None
    }

    with open(HITL_QUEUE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return queue_id


def get_all_reviews() -> List[Dict[str, Any]]:
    """Retrieve all items from the HITL review queue."""
    _ensure_queue_file()
    items = []
    with open(HITL_QUEUE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    # Sort with newest created_at first
    return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)


def get_pending_reviews() -> List[Dict[str, Any]]:
    """Retrieve only items currently pending human review."""
    return [item for item in get_all_reviews() if item.get("status") == "pending_review"]


def resolve_review(
    queue_id: str,
    corrected_json: Dict[str, Any],
    reviewer_notes: str = ""
) -> Tuple[bool, List[str]]:
    """
    Validate the corrected_json against ExtractedDocument schema.
    If valid, marks the queue item as 'resolved' and persists the correction.
    Returns (success: bool, errors: List[str]).
    """
    is_valid, errors = validate_extraction(corrected_json)
    if not is_valid:
        return False, errors

    items = get_all_reviews()
    updated = False
    for item in items:
        if item.get("queue_id") == queue_id or item.get("ticket_id") == queue_id:
            item["status"] = "resolved"
            item["resolved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            item["resolved_json"] = corrected_json
            item["reviewer_notes"] = reviewer_notes
            updated = True
            break

    if updated:
        with open(HITL_QUEUE_FILE, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        return True, []
    
    return False, ["Queue item ID not found in HITL queue."]


def dismiss_review(queue_id: str, reason: str = "") -> bool:
    """Mark a review item as dismissed (e.g. invalid raw data or spam)."""
    items = get_all_reviews()
    updated = False
    for item in items:
        if item.get("queue_id") == queue_id or item.get("ticket_id") == queue_id:
            item["status"] = "dismissed"
            item["resolved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            item["reviewer_notes"] = reason
            updated = True
            break

    if updated:
        with open(HITL_QUEUE_FILE, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        return True
    return False
