"""
Pytest root configuration.

Ensures the project root is in sys.path for all tests.
Provides shared fixtures and helpers.
"""

import sys
import os
import pytest

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def create_test_envelope(
    nation_id: str,
    turn: int = 1,
    defense_payload=None,
    economic_payload=None,
    foreign_payload=None,
    global_strategy=None,
    defense_public_intent=None,
    defense_private_intent=None,
    foreign_public_intent=None,
    foreign_private_intent=None,
    public_statement: str = "Test statement",
):
    """
    Helper to create a CountryEnvelope for testing.
    
    All intents default to IDLE.
    """
    from geomas.agents.schemas import (
        CountryEnvelope, GlobalStrategy,
        DefenseIntentType, ForeignIntentType,
    )
    from geomas.actions.defense import DefensePayload
    from geomas.actions.economy import EconomicPayload
    from geomas.actions.foreign import ForeignPayload
    from geomas.actions.common import Decision
    
    return CountryEnvelope(
        turn=turn,
        sender_id=nation_id,
        global_strategy=global_strategy or GlobalStrategy.ARMED_ISOLATIONISM,
        public_statement=public_statement,
        # Defense
        defense_payload=defense_payload or DefensePayload(decision=Decision.APPROVE),
        defense_public_intent=defense_public_intent or DefenseIntentType.IDLE,
        defense_private_intent=defense_private_intent or DefenseIntentType.IDLE,
        defense_private_reasoning="Test reasoning",
        # Economic
        economic_payload=economic_payload or EconomicPayload(decision=Decision.APPROVE),
        # Foreign
        foreign_payload=foreign_payload or ForeignPayload(decision=Decision.APPROVE),
        foreign_public_intent=foreign_public_intent or ForeignIntentType.IDLE,
        foreign_private_intent=foreign_private_intent or ForeignIntentType.IDLE,
        foreign_private_reasoning="Test reasoning",
    )

