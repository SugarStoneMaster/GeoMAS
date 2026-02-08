import pytest
from pydantic import ValidationError
from geomas.agents.schemas.dynamic import get_dynamic_foreign_proposal
from geomas.actions.foreign.schemas import ForeignPayload, ForeignActionType

def test_dynamic_foreign_proposal_creation():
    valid_ids = ["NATION_A", "NATION_B"]
    DynamicModel = get_dynamic_foreign_proposal(valid_ids)
    
    # Test valid ID
    valid_data = {
        "payload": {
            "decision": "PENDING",
            "action_type": "PROPOSE_ALLIANCE",
            "target_nation_id": "NATION_A"
        },
        "intent": {
            "public_intent": "COOPERATION",
            "private_intent": "COOPERATION",
            "reasoning": "Test reasoning"
        }
    }
    instance = DynamicModel(**valid_data)
    assert instance.payload.target_nation_id == "NATION_A"

    # Test invalid ID
    invalid_data = {
        "payload": {
            "decision": "PENDING",
            "action_type": "PROPOSE_ALLIANCE",
            "target_nation_id": "INVALID_NATION"
        },
        "intent": {
            "public_intent": "COOPERATION",
            "private_intent": "COOPERATION",
            "reasoning": "Test reasoning"
        }
    }
    
    with pytest.raises(ValidationError) as excinfo:
        DynamicModel(**invalid_data)
    
    assert "Input should be 'NATION_A' or 'NATION_B'" in str(excinfo.value)

def test_dynamic_foreign_proposal_empty_list():
    # Should fall back to base class or handle gracefully
    DynamicModel = get_dynamic_foreign_proposal([])
    # If list is empty, target_nation_id might be effectively impossible or Any?
    # Our implementation returns base class if empty
    from geomas.agents.schemas import ForeignProposal
    assert DynamicModel == ForeignProposal
