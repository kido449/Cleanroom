import sys
from pathlib import Path
from typing import Tuple, List, Dict, Any
from pydantic import ValidationError

# Ensure the root project directory (structured-extract) is in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data.schema.schema import ExtractedDocument


def validate_extraction(json_obj: Dict[Any, Any]) -> Tuple[bool, List[str]]:
    """
    Validates a dictionary against the ExtractedDocument Pydantic model.
    Returns:
        tuple[bool, list[str]]: (is_valid, list_of_error_messages)
    """
    try:
        ExtractedDocument.model_validate(json_obj)
        return True, []
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc_str = " -> ".join(str(item) for item in err["loc"])
            msg = err.get("msg", "Validation error")
            if loc_str:
                errors.append(f"{loc_str}: {msg}")
            else:
                errors.append(msg)
        return False, errors
