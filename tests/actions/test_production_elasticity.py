import pytest
from geomas.schemas.world import NationState
from geomas.actions.opinion.handler import get_production_multiplier
from geomas.actions.opinion.schemas import (
    THRESHOLD_PRODUCTION_DECAY_START,
    THRESHOLD_PRODUCTION_DECAY_FLOOR,
    MIN_PRODUCTION_MULTIPLIER
)

def create_mock_nation(satisfaction: float, civil_unrest: bool = False) -> NationState:
    """Helper to create a mock nation with specific satisfaction."""
    return NationState(
        id="test_nation",
        name="Test",
        color="#FFFFFF",
        province_ids=[],
        public_satisfaction=satisfaction,
        civil_unrest_active=civil_unrest
    )

def test_production_multiplier_full():
    """Verify 100% production at or above start threshold."""
    nation = create_mock_nation(THRESHOLD_PRODUCTION_DECAY_START + 10)
    assert get_production_multiplier(nation) == 1.0
    
    nation_at_start = create_mock_nation(THRESHOLD_PRODUCTION_DECAY_START)
    assert get_production_multiplier(nation_at_start) == 1.0

def test_production_multiplier_floor():
    """Verify floor multiplier at or below floor threshold."""
    nation = create_mock_nation(THRESHOLD_PRODUCTION_DECAY_FLOOR)
    assert get_production_multiplier(nation) == MIN_PRODUCTION_MULTIPLIER
    
    nation_below = create_mock_nation(THRESHOLD_PRODUCTION_DECAY_FLOOR - 5)
    assert get_production_multiplier(nation_below) == MIN_PRODUCTION_MULTIPLIER

def test_production_multiplier_linear():
    """Verify linear interpolation halfway through."""
    # Midpoint of 50 and 10 is 30.
    # Midpoint multiplier of 1.0 and 0.5 is 0.75.
    mid_sat = (THRESHOLD_PRODUCTION_DECAY_START + THRESHOLD_PRODUCTION_DECAY_FLOOR) / 2
    nation = create_mock_nation(mid_sat)
    assert get_production_multiplier(nation) == pytest.approx(0.75)
    
    # 1/4 of the way (10 turns above 10 -> Sat 20)
    # 0.5 + (10/40 * 0.5) = 0.5 + 0.125 = 0.625
    nation_q1 = create_mock_nation(20)
    assert get_production_multiplier(nation_q1) == pytest.approx(0.625)

def test_production_multiplier_unrest_override():
    """Verify that civil unrest forces 0.0 production regardless of satisfaction."""
    nation = create_mock_nation(40, civil_unrest=True)
    assert get_production_multiplier(nation) == 0.0
