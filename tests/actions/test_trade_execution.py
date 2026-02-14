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
        total_budget=5000.0, total_materials=0.0,
        total_food=100.0, total_energy=100.0,
        total_population=1000, power_projection=100.0, public_satisfaction=50
    )
    nation_b = NationState(
        id="B", name="Nation B", color="#0000FF", province_ids=[2],
        total_budget=0.0, total_materials=1000.0,
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
        give_type="budget",
        give_amount=300.0,
        want_type="materials"
    )
    
    # Execute
    execute_economic(engine, "A", payload)
    
    # Check Logs
    assert any("ACCEPTED" in log for log in engine.logs)
    
    nation_a = world.nations["A"]
    nation_b = world.nations["B"]
    
    # Check Balances
    # A started with 5000 Budget, 0 Materials
    # Trade: 300 Budget <-> 100 Materials.
    # Receiver B has 1000 Materials. 15% = 150.
    # 100 <= 150. No Receiver Clamp.
    assert nation_a.total_budget == 4700.0
    assert nation_a.total_materials == 100.0
    
    # B started with 0 Budget, 1000 Materials
    assert nation_b.total_budget == 300.0
    assert nation_b.total_materials == 900.0


def test_trade_clamped_instead_of_fail(setup_world):
    """
    Test that asking to give more than you have (or >15%) now gets CLAMPED and SUCCEEDS 
    (instead of failing for returning insufficiency), provided 15% is > 0.
    """
    engine, world = setup_world
    
    # A has 5000 budget (setup). 15% = 750.
    # Try giving 2000.
    payload = EconomicPayload(
        decision=Decision.APPROVE,
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B",
        give_type="budget",
        give_amount=2000.0,
        want_type="materials"
    )
    
    execute_economic(engine, "A", payload)
    
    # Should SUCCEED but with clamped amount (750)
    assert any("Clamped" in log for log in engine.logs)
    assert any("ACCEPTED" in log for log in engine.logs)
    
    # Check A's budget: 5000 - 750 = 4250
    # Wait, does receiver clamp affect this? 
    # B has 1000 Materials (updated setup). 15% = 150.
    # A offers 2000 Budget -> Clamped to 750 Budget.
    # 750 Budget buys 250 Materials (Price 1/3). 
    # Receiver B limit 150 Materials. 
    # 250 > 150. So Receiver Clamps!
    # Receiver Clamps to 150 Materials.
    # 150 Materials costs 450 Budget.
    # So Final Trade: 450 Budget <-> 150 Materials.
    # A's budget: 5000 - 450 = 4550.
    assert world.nations["A"].total_budget == 4550.0


def test_trade_fail_insufficient_receiver(setup_world):
    """Test failure: B doesn't have enough materials to give back."""
    engine, world = setup_world
    
    # A offers 3000 Budget (Value 3000) -> Wants Materials (Price 3) -> Needs 1000 Materials
    # B only has 500 Materials.
    # To offer 3000, A needs 3000 / 0.15 = 20000 Budget to avoid Clamp.
    world.nations["A"].total_budget = 25000.0
    
    payload = EconomicPayload(
        decision=Decision.APPROVE,
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B",
        give_type="budget",
        give_amount=3000.0,
        want_type="materials"
    )
    
    # A offers 3000 Budget.
    # Receiver B has 1000 Materials. 15% = 150.
    # 3000 Budget -> 1000 Materials (Price 1/3).
    # 1000 > 150. Receiver Clamps to 150 Materials.
    # 150 Materials costs 450 Budget.
    # Trade becomes 450 Budget <-> 150 Materials.
    # So it SUCCEEDS (clamped), it does NOT fail for insufficiency.
    
    execute_economic(engine, "A", payload)
    
    # Should SUCCEED clamped
    assert any("ACCEPTED" in log for log in engine.logs)
    assert any("Clamped by RECEIVER" in log for log in engine.logs)
    
    # Check balances
    # A gives 450 Budget (Started 25000) -> 24550
    assert world.nations["A"].total_budget == 24550.0
    # B gives 150 Materials (Started 1000) -> 850
    assert world.nations["B"].total_materials == 850.0


def test_trade_fail_low_trust(setup_world):
    """Test failure: Trust is too low (<40)."""
    engine, world = setup_world
    
    # Set B's trust towards A to 30
    world.trust_matrix["B"]["A"] = 30
    
    payload = EconomicPayload(
        decision=Decision.APPROVE,
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B",
        give_type="budget",
        give_amount=300.0,
        want_type="materials"
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
        give_type="unicorns",
        give_amount=100.0,
        want_type="materials"
    )
    
    execute_economic(engine, "A", payload)
    
    assert any("Failed TRADE_PROPOSAL: Invalid resource" in log for log in engine.logs)


def test_trade_dynamic_trust_gain(setup_world):
    """
    Test dynamic trust gain:
    1. Small trade (100 value) -> Base 2 + 0 = +2
    2. Medium trade (1000 value) -> Base 2 + 2 = +4
    3. Large trade (5000 value) -> Base 2 + 10 = +12 -> Cap +10
    """
    engine, world = setup_world
    
    # Needs enough budget and materials
    world.nations["A"].total_budget = 50000.0 # 15% = 7500 > 5000
    world.nations["B"].total_materials = 50000.0
    
    # Case 1: Small Trade (100 Budget)
    payload_small = EconomicPayload(
        decision=Decision.APPROVE, action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B", give_type="budget", give_amount=100.0,
        want_type="materials"
    )
    execute_economic(engine, "A", payload_small)
    # Trust starts at 50. Gain = 2. Now 52.
    assert world.trust_matrix["A"]["B"] == 52.0
    
    # Case 2: Medium Trade (1000 Budget)
    payload_med = EconomicPayload(
        decision=Decision.APPROVE, action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B", give_type="budget", give_amount=1000.0,
        want_type="materials"
    )
    execute_economic(engine, "A", payload_med)
    # Trust starts at 52. Gain = 2 + (1000/500)=2 = 4. Now 56.
    assert world.trust_matrix["A"]["B"] == 56.0
    
    # Case 3: Large Trade (5000 Budget) -> Gain 2 + 10 = 12 -> Cap 10
    payload_large = EconomicPayload(
        decision=Decision.APPROVE, action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="B", give_type="budget", give_amount=5000.0,
        want_type="materials"
    )
    execute_economic(engine, "A", payload_large)
    # Trust starts at 56. Gain = 10. Now 66.
    assert world.trust_matrix["A"]["B"] == 66.0
