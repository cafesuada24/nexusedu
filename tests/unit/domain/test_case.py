import pytest
from uuid import uuid4
from src.domain.entities.case import Case
from src.domain.exceptions import ValidationError

def test_case_set_ai_overview_success():
    case = Case(sid=uuid4())
    summary = "Student is doing well but needs to focus on Math."
    keys = ["Math practice", "Review homework", "Tutor session"]
    
    case.set_ai_overview(summary, keys)
    
    assert case.academic_summary == summary
    assert case.action_keys == keys

def test_case_set_ai_overview_invariant_violation():
    case = Case(sid=uuid4())
    summary = "Student is failing."
    keys = ["Action 1", "Action 2", "Action 3", "Action 4"]
    
    with pytest.raises(ValidationError, match="Action keys cannot exceed 3 items."):
        case.set_ai_overview(summary, keys)
