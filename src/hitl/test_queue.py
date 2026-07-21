import pytest
from pathlib import Path
from src.hitl.queue import add_to_review_queue, get_pending_reviews, resolve_review, dismiss_review, HITL_QUEUE_FILE


@pytest.fixture(autouse=True)
def clean_queue(monkeypatch, tmp_path):
    """Use a temporary queue file for testing so we don't pollute production queue."""
    temp_file = tmp_path / "test_hitl_queue.jsonl"
    monkeypatch.setattr("src.hitl.queue.HITL_QUEUE_FILE", temp_file)
    yield


def test_add_and_get_pending_reviews():
    qid = add_to_review_queue(
        raw_text="Support text 123",
        last_attempt_json={"customer": {"name": "Test"}},
        last_errors=["issue: Field required"],
        attempts_taken=3,
        ticket_id="TICKET-001"
    )
    assert qid.startswith("Q-")
    
    pending = get_pending_reviews()
    assert len(pending) == 1
    assert pending[0]["ticket_id"] == "TICKET-001"
    assert pending[0]["attempts_taken"] == 3
    assert pending[0]["status"] == "pending_review"


def test_resolve_review_valid_json():
    qid = add_to_review_queue(
        raw_text="Support text 456",
        last_attempt_json={},
        last_errors=["All missing"],
        attempts_taken=3,
        ticket_id="TICKET-002"
    )
    
    # Valid schema object
    valid_doc = {
        "customer": {"name": "Alice"},
        "issue": {"category": "technical", "summary": "Login failed"},
        "resolution": {"status": "open"},
        "metadata": {"tags": []}
    }
    
    success, errors = resolve_review(qid, valid_doc, reviewer_notes="Fixed by Alice")
    assert success is True
    assert errors == []
    
    pending = get_pending_reviews()
    assert len(pending) == 0


def test_resolve_review_invalid_json():
    qid = add_to_review_queue(
        raw_text="Support text 789",
        last_attempt_json={},
        last_errors=["All missing"],
        attempts_taken=3,
        ticket_id="TICKET-003"
    )
    
    # Invalid schema object (missing required fields / invalid enum)
    invalid_doc = {
        "customer": {"name": "Bob", "account_tier": "invalid_tier"}
    }
    
    success, errors = resolve_review(qid, invalid_doc, reviewer_notes="Bad fix")
    assert success is False
    assert len(errors) > 0
    assert any("account_tier" in err for err in errors)
    
    # Still pending
    pending = get_pending_reviews()
    assert len(pending) == 1
    assert pending[0]["status"] == "pending_review"


def test_dismiss_review():
    qid = add_to_review_queue(
        raw_text="Spam text",
        last_attempt_json={},
        last_errors=["Error"],
        attempts_taken=1,
        ticket_id="TICKET-SPAM"
    )
    success = dismiss_review(qid, reason="Spam submission")
    assert success is True
    assert len(get_pending_reviews()) == 0
