import pytest
import sys
import os
from pydantic import ValidationError

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.schemas.protocol import ( 
    DefenseProposal, MilitaryIntent, MilitaryIntentType,
    CountryEnvelope, GlobalStrategy, PublicIntent, EconomicIntent, EconomicPayload, 
    ForeignIntent, ForeignPayload, EconomicIntentType, ForeignIntentType
)
from geomas.schemas.actions import MilitaryPayload, DecisionSource # Updated import

def test_defense_proposal_validation():
    """Test validation constraints on DefenseProposal."""
    
    # Valid
    prop = DefenseProposal(
        intent=MilitaryIntent(type=MilitaryIntentType.DEFENSE, reasoning="Valid"),
        payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
        urgency=5
    )
    assert prop.urgency == 5
    
    # Invalid Urgency (Too high)
    with pytest.raises(ValidationError):
        DefenseProposal(
            intent=MilitaryIntent(type=MilitaryIntentType.DEFENSE, reasoning="Valid"),
            payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
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
            military_payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
            military_intent=MilitaryIntent(type=MilitaryIntentType.IDLE, reasoning="Mock"),
            economic_payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE),
            economic_intent=EconomicIntent(type=EconomicIntentType.IDLE, reasoning="Mock"),
            foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
            foreign_intent=ForeignIntent(type=ForeignIntentType.IDLE, reasoning="Mock")
        )
