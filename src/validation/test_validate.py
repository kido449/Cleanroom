import sys
from pathlib import Path
import pytest

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.validation.validate import validate_extraction


@pytest.fixture
def valid_document_dict():
    return {
        "ticket_id": "TICKET-123",
        "customer": {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "account_tier": "pro"
        },
        "issue": {
            "category": "technical",
            "summary": "Cannot connect to database after recent update.",
            "priority": "high"
        },
        "resolution": {
            "status": "in_progress",
            "resolution_notes": "Investigating connection pooling timeout.",
            "assigned_agent": "Agent Smith"
        },
        "metadata": {
            "created_at": "2026-07-17T10:00:00Z",
            "tags": ["db", "timeout", "urgent-review"]
        }
    }


def test_validate_extraction_valid(valid_document_dict):
    is_valid, errors = validate_extraction(valid_document_dict)
    assert is_valid is True
    assert errors == []


def test_validate_extraction_wrong_enum(valid_document_dict):
    invalid_dict = dict(valid_document_dict)
    invalid_dict["customer"] = dict(valid_document_dict["customer"])
    invalid_dict["customer"]["account_tier"] = "super_premium"  # Not in ["free", "pro", "enterprise"]

    is_valid, errors = validate_extraction(invalid_dict)
    assert is_valid is False
    assert len(errors) > 0
    assert any("customer -> account_tier" in err for err in errors)


def test_validate_extraction_missing_required_field(valid_document_dict):
    invalid_dict = dict(valid_document_dict)
    invalid_dict["issue"] = dict(valid_document_dict["issue"])
    del invalid_dict["issue"]["summary"]

    is_valid, errors = validate_extraction(invalid_dict)
    assert is_valid is False
    assert len(errors) > 0
    assert any("issue -> summary" in err for err in errors)
