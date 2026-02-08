"""
Tests for Trade Execution logic (handler.py).
Verifies single-resource trade proposals and deterministic acceptance.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.actions.engine import ActionEngine
from geomas.actions.economy import EconomicPayload, EconomicActionType, BASE_PRICES, execute_economic
from geomas.actions.common import Decision
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType


@pytest.fixture
def setup_world():
    """Setup world with 2 nations (A and B)."""
    nation_a = NationState(
        id="A", name="Nation A", color="#FF0000", province_ids=[1],
        total_budget=1000.0, total_materials=0.0,
        total_food=100.0, total_energy=100.0,
        total_population=1000, power_projection=100.0, public_satisfaction=50
    )
    nation_b = NationState(
        id="B", name="Nation B", color="#0000FF", province_ids=[2],
        total_budget=0.0, total_materials=500.0,
        total_food=100.0, total_energy=100.0,
        total_population=1000, power_projection=100.0, public_satisfaction=50
    )
    
    provinces = {
        1: ProvinceState(id=1, owner_id="A", terrain=TerrainType.LAND, coordinates=(0,0), population=1000, workers=100),
        2: ProvinceState(id=2, owner_id="B", terrain=TerrainType.LAND, coordinates=(0,0), population=1000, workers=100),
    }

    world = WorldState(
        turn=1, provinces=provinces, nations={"A": nation_a, "B": nation_b},
        trust_matrix={"A": {"B": 50}, "B": {"A": 50}} # Neutral trust
    )
    
    engine = ActionEngine(world)
    return engine, world


def test_trade_success_budget_for_materials(setup_world):
    """
    Test successful trade: A gives 300 Budget for Materials.
    Market Rates: Budget=1, Materials=3.
    Expect: A gives 300 Budget, Receives 100 Materials. B gives 100 Materials, Receives 300 Budget.
    """
    engine, world = setup_world
    
    payload = EconomicPayload(
        decision=Decision.APPROVE,
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B",
        trade_offer_give_type="budget",
        trade_offer_give_amount=300.0,
        trade_offer_want_type="materials"
    )
    
    # Execute
    execute_economic(engine, "A", payload)
    
    # Check Logs
    assert any("ACCEPTED" in log for log in engine.logs)
    
    nation_a = world.nations["A"]
    nation_b = world.nations["B"]
    
    # Check Balances
    # A started with 1000 Budget, 0 Materials
    assert nation_a.total_budget == 700.0
    assert nation_a.total_materials == 100.0
    
    # B started with 0 Budget, 500 Materials
    assert nation_b.total_budget == 300.0
    assert nation_b.total_materials == 400.0


def test_trade_fail_insufficient_giver(setup_world):
    """Test failure: A tries to give budget it doesn't have."""
    engine, world = setup_world
    
    payload = EconomicPayload(
        decision=Decision.APPROVE,
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B",
        trade_offer_give_type="budget",
        trade_offer_give_amount=2000.0, # More than 1000
        trade_offer_want_type="materials"
    )
    
    execute_economic(engine, "A", payload)
    
    assert any("REJECTED" in log for log in engine.logs)
    assert any("Sender insufficiency" in log for log in engine.logs)
    
    # Balances unchanged
    assert world.nations["A"].total_budget == 1000.0


def test_trade_fail_insufficient_receiver(setup_world):
    """Test failure: B doesn't have enough materials to give back."""
    engine, world = setup_world
    
    # A offers 3000 Budget (Value 3000) -> Wants Materials (Price 3) -> Needs 1000 Materials
    # B only has 500 Materials.
    # But wait, A only has 1000 Budget, so let's give A infinite budget first to isolate receiver check.
    world.nations["A"].total_budget = 5000.0
    
    payload = EconomicPayload(
        decision=Decision.APPROVE,
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B",
        trade_offer_give_type="budget",
        trade_offer_give_amount=3000.0,
        trade_offer_want_type="materials"
    )
    
    execute_economic(engine, "A", payload)
    
    assert any("REJECTED" in log for log in engine.logs)
    assert any("Receiver insufficiency" in log for log in engine.logs)


def test_trade_fail_low_trust(setup_world):
    """Test failure: Trust is too low (<40)."""
    engine, world = setup_world
    
    # Set B's trust towards A to 30
    world.trust_matrix["B"]["A"] = 30
    
    payload = EconomicPayload(
        decision=Decision.APPROVE,
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B",
        trade_offer_give_type="budget",
        trade_offer_give_amount=300.0,
        trade_offer_want_type="materials"
    )
    
    execute_economic(engine, "A", payload)
    
    assert any("REJECTED" in log for log in engine.logs)
    assert any("Trust too low" in log for log in engine.logs)


def test_trade_fail_invalid_resource(setup_world):
    """Test failure: Invalid resource type."""
    engine, world = setup_world
    
    payload = EconomicPayload(
        decision=Decision.APPROVE,
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B",
        trade_offer_give_type="unicorns",
        trade_offer_give_amount=100.0,
        trade_offer_want_type="materials"
    )
    
    execute_economic(engine, "A", payload)
    
    assert any("Failed TRADE_PROPOSAL: Invalid resource" in log for log in engine.logs)
