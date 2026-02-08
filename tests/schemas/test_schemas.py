"""
Tests for Schema Validation.

Validates Pydantic models and constraints.
"""

import pytest
import sys
import os
from pydantic import ValidationError

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.agents.schemas import ( 
    DefenseProposal, DefenseIntent, DefenseIntentType,
    CountryEnvelope, GlobalStrategy, EconomicIntent,
    ForeignIntent, EconomicIntentType, ForeignIntentType
)
from geomas.actions.defense import DefensePayload, Decision
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload


def test_defense_proposal_validation():
    """Test validation constraints on DefenseProposal."""
    
    # Valid
    prop = DefenseProposal(
        intent=DefenseIntent(
            public_intent=DefenseIntentType.DEFENSE,
            private_intent=DefenseIntentType.DEFENSE,
            reasoning="Valid"
        ),
        payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
        urgency=5
    )
    assert prop.urgency == 5
    
    # Invalid Urgency (Too high)
    with pytest.raises(ValidationError):
        DefenseProposal(
            intent=DefenseIntent(
                public_intent=DefenseIntentType.DEFENSE,
                private_intent=DefenseIntentType.DEFENSE,
                reasoning="Valid"
            ),
            payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
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
            # Missing public_statement -> should fail
            defense_payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
            defense_private_reasoning="Test",
            economic_payload=EconomicPayload(decision=Decision.APPROVE),
            economic_public_intent=EconomicIntentType.IDLE,
            economic_private_intent=EconomicIntentType.IDLE,
            economic_private_reasoning="Test",
            foreign_payload=ForeignPayload(decision=Decision.APPROVE),
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
            foreign_private_reasoning="Test"
        )


def test_envelope_valid():
    """Test valid CountryEnvelope creation."""
    
    envelope = CountryEnvelope(
        turn=1,
        sender_id="TEST",
        global_strategy=GlobalStrategy.COALITION_BUILDER,
        public_statement="[DEFENSE] Peaceful. [ECONOMY] Growing. [FOREIGN] Cooperative.",
        # Defense
        defense_payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
        defense_public_intent=DefenseIntentType.DEFENSE,
        defense_private_intent=DefenseIntentType.IDLE,
        defense_private_reasoning="Maintaining peace.",
        # Economic
        economic_payload=EconomicPayload(decision=Decision.APPROVE),
        economic_public_intent=EconomicIntentType.GROWTH,
        economic_private_intent=EconomicIntentType.GROWTH,
        economic_private_reasoning="Investing in welfare.",
        # Foreign
        foreign_payload=ForeignPayload(decision=Decision.APPROVE),
        foreign_public_intent=ForeignIntentType.COOPERATION,
        foreign_private_intent=ForeignIntentType.COOPERATION,
        foreign_private_reasoning="Seeking alliances."
    )
    
    assert envelope.sender_id == "TEST"
    assert envelope.defense_public_intent == DefenseIntentType.DEFENSE
    assert envelope.defense_private_intent == DefenseIntentType.IDLE
