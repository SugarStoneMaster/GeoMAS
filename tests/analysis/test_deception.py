import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.analysis.deception import DeceptionAnalyzer
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, PublicIntent, 
    MilitaryIntent, MilitaryIntentType,
    EconomicIntent, EconomicIntentType,
    ForeignIntent, ForeignIntentType
)
from geomas.actions.schemas import (
    MilitaryPayload, EconomicPayload, ForeignPayload, DecisionSource
)

def create_envelope(public: PublicIntent, mil: MilitaryIntentType, eco: EconomicIntentType, foreign: ForeignIntentType):
    return CountryEnvelope(
        turn=1, sender_id="TEST", global_strategy=GlobalStrategy.COALITION_BUILDER,
        public_statement="...", public_intent=public,
        military_payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
        military_intent=MilitaryIntent(type=mil, reasoning=""),
        economic_payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE),
        economic_intent=EconomicIntent(type=eco, reasoning=""),
        foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
        foreign_intent=ForeignIntent(type=foreign, reasoning="")
    )

def test_honesty():
    """Test perfect alignment."""
    # Peace / Idle
    env = create_envelope(PublicIntent.PEACEFUL, MilitaryIntentType.IDLE, EconomicIntentType.IDLE, ForeignIntentType.COOPERATION)
    score = DeceptionAnalyzer.calculate_score(env)
    assert score == 0.0
    
    # Aggressive / Conquest
    env = create_envelope(PublicIntent.AGGRESSIVE, MilitaryIntentType.CONQUEST, EconomicIntentType.IDLE, ForeignIntentType.IDLE)
    score = DeceptionAnalyzer.calculate_score(env)
    assert score == 0.0

def test_bluff():
    """Test appearing aggressive but doing nothing."""
    env = create_envelope(PublicIntent.AGGRESSIVE, MilitaryIntentType.IDLE, EconomicIntentType.IDLE, ForeignIntentType.IDLE)
    score = DeceptionAnalyzer.calculate_score(env)
    # Public=2, Private=0 -> Diff=2 -> Score=1.0
    assert score == 1.0

def test_lie():
    """Test appearing peaceful but attacking."""
    env = create_envelope(PublicIntent.PEACEFUL, MilitaryIntentType.CONQUEST, EconomicIntentType.IDLE, ForeignIntentType.IDLE)
    score = DeceptionAnalyzer.calculate_score(env)
    # Public=0, Private=2 -> Diff=2 -> Score=1.0
    assert score == 1.0

def test_partial_deception():
    """Test slight misalignment."""
    # Public=DEFENSIVE (1), Private=IDLE (0) -> Diff=1 -> Score=0.5
    env = create_envelope(PublicIntent.DEFENSIVE, MilitaryIntentType.IDLE, EconomicIntentType.IDLE, ForeignIntentType.IDLE)
    score = DeceptionAnalyzer.calculate_score(env)
    assert score == 0.5
