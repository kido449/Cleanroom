import sys
from pathlib import Path
from typing import List, Tuple, Optional, Any, Dict
import pytest

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.extraction.pipeline import extract_with_repair


class MockExtractor:
    def __init__(self, responses: List[Any]):
        self.responses = responses
        self.calls: List[Tuple[str, Optional[str]]] = []

    def extract(self, text: str, prompt_override: Optional[str] = None) -> Dict[str, Any]:
        self.calls.append((text, prompt_override))
        if not self.responses:
            raise RuntimeError("MockExtractor ran out of pre-configured responses")
        res = self.responses.pop(0)
        if isinstance(res, Exception):
            raise res
        return res


@pytest.fixture
def valid_dict() -> Dict[str, Any]:
    return {
        "ticket_id": "T-100",
        "customer": {"name": "Alice", "email": "alice@example.com", "account_tier": "pro"},
        "issue": {"category": "technical", "summary": "Can't connect to DB", "priority": "high"},
        "resolution": {"status": "open", "resolution_notes": None, "assigned_agent": None},
        "metadata": {"created_at": "2026-07-18T10:00:00Z", "tags": ["db"]}
    }


def test_extract_with_repair_first_attempt_succeeds(valid_dict):
    mock_extractor = MockExtractor(responses=[valid_dict])
    result = extract_with_repair("Can't connect to database", max_retries=3, extractor=mock_extractor)
    
    assert result["status"] == "success"
    assert result["attempts"] == 1
    assert result["errors_encountered"] == []
    assert result["data"] == valid_dict
    assert len(mock_extractor.calls) == 1
    assert mock_extractor.calls[0][1] is None  # No prompt_override on first attempt


def test_extract_with_repair_second_attempt_succeeds(valid_dict):
    # First attempt returns invalid enum (`super_premium`)
    invalid_dict = {
        "ticket_id": "T-100",
        "customer": {"name": "Alice", "email": "alice@example.com", "account_tier": "super_premium"},
        "issue": {"category": "technical", "summary": "Can't connect to DB", "priority": "high"},
        "resolution": {"status": "open", "resolution_notes": None, "assigned_agent": None},
        "metadata": {"created_at": "2026-07-18T10:00:00Z", "tags": ["db"]}
    }
    mock_extractor = MockExtractor(responses=[invalid_dict, valid_dict])
    result = extract_with_repair("Can't connect to database", max_retries=3, extractor=mock_extractor)
    
    assert result["status"] == "success"
    assert result["attempts"] == 2
    assert len(result["errors_encountered"]) == 1
    assert any("customer -> account_tier" in err for err in result["errors_encountered"][0])
    assert result["data"] == valid_dict
    assert len(mock_extractor.calls) == 2
    
    # Verify second call received the correction prompt with specific validation error
    assert mock_extractor.calls[1][1] is not None
    assert "VALIDATION ERRORS ENCOUNTERED" in mock_extractor.calls[1][1]
    assert "customer -> account_tier" in mock_extractor.calls[1][1]


def test_extract_with_repair_all_attempts_fail():
    invalid_dict = {
        "customer": {"account_tier": "bad_tier"},
        "issue": {"summary": "Broken app"}  # missing category, required fields, etc.
    }
    mock_extractor = MockExtractor(responses=[invalid_dict, invalid_dict, invalid_dict])
    result = extract_with_repair("Broken app", max_retries=3, extractor=mock_extractor)
    
    assert result["status"] == "flagged_for_review"
    assert result["attempts"] == 3
    assert result["raw_text"] == "Broken app"
    assert result["last_attempt_json"] == invalid_dict
    assert len(result["last_errors"]) > 0
    assert len(mock_extractor.calls) == 3


def test_extract_with_repair_api_error_raised_separately():
    class FakeAPIError(Exception):
        pass
    
    mock_extractor = MockExtractor(responses=[FakeAPIError("Network timeout after tenacity retries exhausted")])
    with pytest.raises(FakeAPIError) as exc_info:
        extract_with_repair("Some text", max_retries=3, extractor=mock_extractor)
    
    assert "Network timeout after tenacity retries exhausted" in str(exc_info.value)
    assert len(mock_extractor.calls) == 1
