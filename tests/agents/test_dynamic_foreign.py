import pytest
from pydantic import ValidationError
from geomas.agents.schemas.dynamic import get_dynamic_proposal_model
from geomas.agents.schemas import ForeignProposal, EconomicProposal, DefenseProposal

def test_dynamic_foreign_proposal():
    valid_ids = ["NATION_A", "NATION_B"]
    DynamicModel = get_dynamic_proposal_model(ForeignProposal, valid_ids)
    
    # Test valid
    valid_data = {
        "payload": {
            "decision": "PENDING",
            "action_type": "PROPOSE_ALLIANCE",
            "target_nation_id": "NATION_A"
        },
        "intent": {"public_intent": "COOPERATION", "private_intent": "COOPERATION", "reasoning": "Test"}
    }
    instance = DynamicModel(**valid_data)
    assert instance.payload.target_nation_id == "NATION_A"

    # Test invalid
    invalid_data = valid_data.copy()
    invalid_data["payload"] = valid_data["payload"].copy()
    invalid_data["payload"]["target_nation_id"] = "INVALID"
    
    with pytest.raises(ValidationError) as excinfo:
        DynamicModel(**invalid_data)
    assert "Input should be 'NATION_A' or 'NATION_B'" in str(excinfo.value)

def test_dynamic_economic_proposal():
    valid_ids = ["NATION_X", "NATION_Y"]
    DynamicModel = get_dynamic_proposal_model(EconomicProposal, valid_ids)
    
    # Test valid
    valid_data = {
        "payload": {
            "decision": "PENDING",
            "action_type": "TRADE_PROPOSAL",
            "target_nation_id": "NATION_X",
            "give_type": "food",
            "give_amount": 100.0,
            "want_type": "energy",
            "amount": 0, # Optional but good to be explicit
            "message": "Trade"
        },
        "intent": {"public_intent": "GROWTH", "private_intent": "GROWTH", "reasoning": "Test"}
    }
    instance = DynamicModel(**valid_data)
    assert instance.payload.target_nation_id == "NATION_X"
    
    # Test invalid
    invalid_data = valid_data.copy()
    invalid_data["payload"] = valid_data["payload"].copy()
    invalid_data["payload"]["target_nation_id"] = "INVALID"
    
    with pytest.raises(ValidationError):
        DynamicModel(**invalid_data)

def test_dynamic_defense_proposal():
    valid_ids = ["ENEMY_1", "ENEMY_2"]
    DynamicModel = get_dynamic_proposal_model(DefenseProposal, valid_ids)
    
    # Test valid
    valid_data = {
        "payload": {
            "decision": "PENDING",
            "moves": [
                {
                    "priority": 1,
                    "action_type": "MOVE_TROOPS",
                    "target_nation_id": "ENEMY_1",
                    # Added required fields to pass strict schema validation
                    "unit_type": "SOLDIER",
                    "quantity": 10,
                    "source_province_id": 1,
                    "target_province_id": 2
                }
            ]
        },
        "intent": {"public_intent": "DETERRENCE", "private_intent": "DETERRENCE", "reasoning": "Test"}
    }
    instance = DynamicModel(**valid_data)
    assert instance.payload.moves[0].target_nation_id == "ENEMY_1"
    
    # Test invalid in nesting
    invalid_data = {
        "payload": {
            "decision": "PENDING",
            "moves": [
                {
                    "priority": 1,
                    "action_type": "MOVE_TROOPS",
                    "target_nation_id": "INVALID_ENEMY",
                    # Added required fields
                    "unit_type": "SOLDIER",
                    "quantity": 10,
                    "source_province_id": 1,
                    "target_province_id": 2
                }
            ]
        },
        "intent": {"public_intent": "DETERRENCE", "private_intent": "DETERRENCE", "reasoning": "Test"}
    }
    
    with pytest.raises(ValidationError):
        DynamicModel(**invalid_data)
