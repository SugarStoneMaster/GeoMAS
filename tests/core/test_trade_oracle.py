"""
Tests for the trade oracle module.
"""

import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.core.trade_oracle import (
    TradeOffer,
    calculate_scarcity_multiplier,
    calculate_relational_risk,
    calculate_power_projection_impact,
    calculate_trade_score,
    evaluate_trade,
    BASE_PRICES
)
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType, MinisterialState


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
        total_soldiers=500,
        total_aircraft=10,
        total_navy=20,
        nukes=0,
        power_projection=100.0,
        internal_state=MinisterialState(budget=1000.0, public_satisfaction=0.5)
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
        total_food=50.0,   # Scarce
        total_energy=30.0,  # Scarce
        total_materials=100.0,
        total_population=5000,
        total_soldiers=200,
        total_aircraft=5,
        total_navy=10,
        nukes=0,
        power_projection=50.0,
        internal_state=MinisterialState(budget=500.0, public_satisfaction=0.5)
    )


@pytest.fixture
def sample_world(nation_a, nation_b):
    """World with two nations."""
    provinces = {
        1: ProvinceState(
            id=1, owner_id="A", terrain=TerrainType.LAND,
            coordinates=(0.3, 0.5), population=10000, workers=9500
        ),
        2: ProvinceState(
            id=2, owner_id="B", terrain=TerrainType.LAND,
            coordinates=(0.7, 0.5), population=5000, workers=4800
        ),
    }
    
    return WorldState(
        turn=1,
        provinces=provinces,
        nations={"A": nation_a, "B": nation_b},
        trust_matrix={
            "A": {"B": 0.6},
            "B": {"A": 0.6}
        }
    )


# --- SCARCITY TESTS ---

class TestScarcityMultiplier:
    def test_abundant_stock(self):
        """Abundant stock (5+ turns) = 1.0 multiplier."""
        multiplier = calculate_scarcity_multiplier("food", current_stock=1000, consumption_per_turn=100)
        assert multiplier == 1.0
    
    def test_comfortable_stock(self):
        """Comfortable stock (3-5 turns) = 1.5 multiplier."""
        multiplier = calculate_scarcity_multiplier("food", current_stock=400, consumption_per_turn=100)
        assert multiplier == 1.5
    
    def test_tight_stock(self):
        """Tight stock (1-3 turns) = 2.5 multiplier."""
        multiplier = calculate_scarcity_multiplier("food", current_stock=200, consumption_per_turn=100)
        assert multiplier == 2.5
    
    def test_critical_stock(self):
        """Critical stock (<1 turn) = 4.0 multiplier."""
        multiplier = calculate_scarcity_multiplier("food", current_stock=50, consumption_per_turn=100)
        assert multiplier == 4.0
    
    def test_zero_stock(self):
        """Zero stock = 5.0 multiplier."""
        multiplier = calculate_scarcity_multiplier("food", current_stock=0, consumption_per_turn=100)
        assert multiplier == 5.0
    
    def test_zero_consumption(self):
        """Zero consumption = 1.0 multiplier (no scarcity concern)."""
        multiplier = calculate_scarcity_multiplier("food", current_stock=100, consumption_per_turn=0)
        assert multiplier == 1.0


# --- RELATIONAL RISK TESTS ---

class TestRelationalRisk:
    def test_high_trust(self):
        """High trust (>= 0.5) = 0 risk."""
        assert calculate_relational_risk(0.5) == 0.0
        assert calculate_relational_risk(0.8) == 0.0
        assert calculate_relational_risk(1.0) == 0.0
    
    def test_low_trust(self):
        """Low trust (< 0.5) = risk proportional to distrust."""
        # trust=0.3 -> (50 - 30) / 10 = 2.0
        assert calculate_relational_risk(0.3) == 2.0
        
        # trust=0.1 -> (50 - 10) / 10 = 4.0
        assert calculate_relational_risk(0.1) == 4.0
        
        # trust=0.0 -> (50 - 0) / 10 = 5.0
        assert calculate_relational_risk(0.0) == 5.0


# --- POWER PROJECTION IMPACT TESTS ---

class TestPowerProjectionImpact:
    def test_non_strategic_resource(self):
        """Non-strategic resources (food) have 0 impact."""
        impact = calculate_power_projection_impact("food", receiver_power=100.0, sender_power=50.0)
        assert impact == 0.0
    
    def test_strategic_resource_weaker_receiver(self):
        """Weaker receiver = 0 impact, no concern."""
        impact = calculate_power_projection_impact("materials", receiver_power=25.0, sender_power=50.0)
        assert impact == 0.0
    
    def test_strategic_resource_comparable_power(self):
        """Comparable power = moderate impact."""
        impact = calculate_power_projection_impact("materials", receiver_power=50.0, sender_power=50.0)
        assert impact == 0.5
    
    def test_strategic_resource_stronger_receiver(self):
        """Stronger receiver = higher impact."""
        impact = calculate_power_projection_impact("materials", receiver_power=75.0, sender_power=50.0)
        assert impact == 1.0
    
    def test_strategic_resource_much_stronger_receiver(self):
        """Much stronger receiver = max impact."""
        impact = calculate_power_projection_impact("materials", receiver_power=100.0, sender_power=50.0)
        assert impact == 2.0


# --- TRADE SCORE TESTS ---

class TestTradeScore:
    def test_beneficial_trade_accepted(self, sample_world):
        """Trade where receiver gets high-value scarce resources is accepted."""
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 100.0},  # A gives food
            receive={"materials": 30.0}  # A receives materials
        )
        
        score, explanation = calculate_trade_score(offer, sample_world)
        # B has scarce food, so this should be beneficial
        assert score > 0, f"Expected positive score, got {score}: {explanation}"
    
    def test_unfavorable_trade_rejected(self, sample_world):
        """Trade where receiver gives too much is rejected."""
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 10.0},  # A gives little food
            receive={"materials": 200.0}  # A wants lots of materials
        )
        
        score, explanation = calculate_trade_score(offer, sample_world)
        # B is giving way more than receiving
        assert score < 0, f"Expected negative score, got {score}: {explanation}"


# --- EVALUATE TRADE TESTS ---

class TestEvaluateTrade:
    def test_evaluate_accepted(self, sample_world):
        """Beneficial trades are accepted."""
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 100.0},
            receive={"materials": 20.0}
        )
        
        accepted, explanation = evaluate_trade(offer, sample_world)
        assert accepted is True
        assert "ACCEPTED" in explanation
    
    def test_evaluate_rejected(self, sample_world):
        """Unfavorable trades are rejected."""
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 5.0},
            receive={"materials": 100.0}
        )
        
        accepted, explanation = evaluate_trade(offer, sample_world)
        assert accepted is False
        assert "REJECTED" in explanation


# --- TRADE OFFER SCHEMA TESTS ---

class TestTradeOfferSchema:
    def test_trade_offer_creation(self):
        """TradeOffer can be created with valid data."""
        offer = TradeOffer(
            sender_id="A",
            receiver_id="B",
            give={"food": 100.0, "energy": 50.0},
            receive={"materials": 30.0},
            duration_turns=3
        )
        
        assert offer.sender_id == "A"
        assert offer.receiver_id == "B"
        assert offer.give == {"food": 100.0, "energy": 50.0}
        assert offer.receive == {"materials": 30.0}
        assert offer.duration_turns == 3
    
    def test_trade_offer_defaults(self):
        """TradeOffer has correct defaults."""
        offer = TradeOffer(sender_id="X", receiver_id="Y")
        
        assert offer.give == {}
        assert offer.receive == {}
        assert offer.duration_turns == 1


# --- BASE PRICES TESTS ---

class TestBasePrices:
    def test_prices_defined(self):
        """All resource types have base prices."""
        assert "food" in BASE_PRICES
        assert "energy" in BASE_PRICES
        assert "materials" in BASE_PRICES
    
    def test_price_ordering(self):
        """Materials > Energy > Food in value."""
        assert BASE_PRICES["materials"] > BASE_PRICES["energy"]
        assert BASE_PRICES["energy"] > BASE_PRICES["food"]
