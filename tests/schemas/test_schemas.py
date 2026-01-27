import pytest
import sys
import os
from pydantic import ValidationError

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.agents.schemas import ( 
    DefenseProposal, DefenseIntent, DefenseIntentType,
    CountryEnvelope, GlobalStrategy, PublicIntent, EconomicIntent,
    ForeignIntent, EconomicIntentType, ForeignIntentType
)
from geomas.actions.defense import DefensePayload, DecisionSource
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload

def test_defense_proposal_validation():
    """Test validation constraints on DefenseProposal."""
    
    # Valid
    prop = DefenseProposal(
        intent=DefenseIntent(type=DefenseIntentType.DEFENSE, reasoning="Valid"),
        payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
        urgency=5
    )
    assert prop.urgency == 5
    
    # Invalid Urgency (Too high)
    with pytest.raises(ValidationError):
        DefenseProposal(
            intent=DefenseIntent(type=DefenseIntentType.DEFENSE, reasoning="Valid"),
            payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
            urgency=11 # Max is 10
        )

def test_envelope_structure():
    """Test that CountryEnvelope requires all fields."""
    
    # Missing fields should raise error
    with pytest.raises(ValidationError):
        CountryEnvelope(
            turn=1,
            sender_id="TEST",
            global_strategy=GlobalStrategy.COALITION_BUILDER,
            # Missing public_statement
            public_intent=PublicIntent.PEACEFUL,
            defense_payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
            defense_intent=DefenseIntent(type=DefenseIntentType.IDLE, reasoning="Mock"),
            economic_payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE),
            economic_intent=EconomicIntent(type=EconomicIntentType.IDLE, reasoning="Mock"),
            foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
            foreign_intent=ForeignIntent(type=ForeignIntentType.IDLE, reasoning="Mock")
        )
