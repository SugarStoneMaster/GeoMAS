"""
Tests for the deterministic trade oracle module.
"""

import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.actions.economy import (
    TradeOffer,
    evaluate_trade,
    BASE_PRICES
)
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType


# --- FIXTURES ---

@pytest.fixture
def nation_a():
    """Sender nation - moderate resources."""
    return NationState(
        id="A",
        name="Nation A",
        color="#FF0000",
        province_ids=[1],
        total_budget=1000.0,
        total_food=500.0,
        total_energy=300.0,
        total_materials=200.0,
        total_population=10000,
        power_projection=100.0,
        public_satisfaction=50
    )


@pytest.fixture
def nation_b():
    """Receiver nation - scarce resources."""
    return NationState(
        id="B",
        name="Nation B",
        color="#0000FF",
        province_ids=[2],
        total_budget=500.0,
        total_food=50.0,   
        total_energy=30.0,
        total_materials=100.0,
        total_population=5000,
        power_projection=50.0,
        public_satisfaction=50
    )


@pytest.fixture
def sample_world(nation_a, nation_b):
    """World with two nations."""
    provinces = {
        1: ProvinceState(id=1, owner_id="A", terrain=TerrainType.LAND, coordinates=(0,0), population=1000, workers=100),
        2: ProvinceState(id=2, owner_id="B", terrain=TerrainType.LAND, coordinates=(0,0), population=1000, workers=100),
    }
    
    return WorldState(
        turn=1,
        provinces=provinces,
        nations={"A": nation_a, "B": nation_b},
        trust_matrix={
            "A": {"B": 60}, # Trust from A to B (irrelevant for acceptance)
            "B": {"A": 50}  # Trust from B to A (Receiver to Sender) -> 50 >= 40 (Neutral)
        }
    )


# --- DETERMINISTIC TRADE EVALUATION TESTS ---

class TestEvaluateTrade:
    
    def test_evaluate_accepted_neutral_trust(self, sample_world):
        """Trade accepted when trust >= 40 and balances sufficient."""
        # A gives 100 food (A has 500), B gives 20 materials (B has 100)
        # Trust B->A is 50 (Neutral)
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 100.0},
            receive={"materials": 20.0}
        )
        
        accepted, explanation = evaluate_trade(offer, sample_world)
        assert accepted is True, f"Trade rejected: {explanation}"
        assert "Conditions met" in explanation

    def test_evaluate_rejected_low_trust(self, sample_world):
        """Trade rejected when trust < 40."""
        # Lower trust B->A to 30 (Distrustful)
        sample_world.trust_matrix["B"]["A"] = 30
        
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 100.0},
            receive={"materials": 1.0}
        )
        
        accepted, explanation = evaluate_trade(offer, sample_world)
        assert accepted is False
        assert "Trust too low" in explanation

    def test_evaluate_rejected_sender_insufficient(self, sample_world):
        """Trade rejected when Sender (A) lacks resources."""
        # A has 500 food, tries to give 600
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 600.0},
            receive={"materials": 1.0}
        )
        
        accepted, explanation = evaluate_trade(offer, sample_world)
        assert accepted is False
        assert "Sender insufficiency" in explanation

    def test_evaluate_rejected_receiver_insufficient(self, sample_world):
        """Trade rejected when Receiver (B) lacks resources."""
        # B has 100 materials, asked to give 150
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 1.0},
            receive={"materials": 150.0}
        )
        
        accepted, explanation = evaluate_trade(offer, sample_world)
        assert accepted is False
        assert "Receiver insufficiency" in explanation

    def test_implicit_trust_defaults(self, sample_world):
        """Default trust is 50 (Neutral), so trade accepted."""
        # Remove explicit trust
        sample_world.trust_matrix = {}
        
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 10.0},
            receive={"materials": 1.0}
        )
        
        accepted, explanation = evaluate_trade(offer, sample_world)
        assert accepted is True


# --- BASE PRICES TESTS ---

class TestBasePrices:
    def test_prices_defined(self):
        """All resource types have base prices."""
        assert "food" in BASE_PRICES
        assert "energy" in BASE_PRICES
        assert "materials" in BASE_PRICES
        assert "budget" in BASE_PRICES
    
    def test_price_ordering(self):
        """Materials > Energy > Food/Budget in value."""
        assert BASE_PRICES["materials"] > BASE_PRICES["energy"]
        assert BASE_PRICES["energy"] > BASE_PRICES["food"]
        assert BASE_PRICES["budget"] == 1.0
