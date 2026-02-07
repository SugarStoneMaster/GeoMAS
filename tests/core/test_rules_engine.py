"""
Tests for Rules Engine.

Validates movement, economic, and diplomatic rules.
"""

import pytest
import sys
import os

# Add project root to path (Two levels up)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from conftest import create_test_envelope
from geomas.world import generate_world
from geomas.actions import ActionEngine
from geomas.actions.defense import DefensePayload, DefenseActionItem, DefenseActionType, Decision
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload
from geomas.agents.schemas import DefenseIntentType


def test_movement_rules():
    """Test topological movement constraints."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    engine = ActionEngine(world)
    
    nation_id = list(world.nations.keys())[0]
    my_provinces = world.nations[nation_id].province_ids
    
    # 1. Valid Move (Internal)
    p1 = my_provinces[0]
    p2 = None
    for n in world.provinces[p1].neighbors:
        if n in world.provinces and n in my_provinces: 
            p2 = n
            break
            
    if p2:
        allowed, reason = engine.can_move_troops(nation_id, p1, p2)
        assert allowed, f"Should allow internal move: {reason}"
    
    # 2. Invalid Move (To Enemy)
    enemy_id = list(world.nations.keys())[1]
    enemy_prov = world.nations[enemy_id].province_ids[0]
    
    allowed, reason = engine.can_move_troops(nation_id, p1, enemy_prov)
    assert not allowed
    assert "foreign" in reason or "ATTACK" in reason


def test_economic_rules():
    """Test budget constraints."""
    world = generate_world(seed=42, n_cells=50, n_nations=1)
    engine = ActionEngine(world)
    nation_id = list(world.nations.keys())[0]
    
    # Set budget (use total_budget)
    world.nations[nation_id].total_budget = 100.0
    
    # Affordable
    allowed, _ = engine.can_afford_budget(nation_id, 50.0)
    assert allowed
    
    # Too expensive
    allowed, reason = engine.can_afford_budget(nation_id, 150.0)
    assert not allowed
    assert "Insufficient" in reason


def test_diplomatic_rules():
    """Test trade constraints based on trust."""
    world = generate_world(seed=42, n_cells=50, n_nations=2)
    engine = ActionEngine(world)
    
    n_a = list(world.nations.keys())[0]
    n_b = list(world.nations.keys())[1]
    
    # Case 1: High Trust (0-100 scale)
    world.trust_matrix[n_a][n_b] = 80
    allowed, _ = engine.can_trade(n_a, n_b)
    assert allowed
    
    # Case 2: Low Trust (< 20 = hostile, trade blocked)
    world.trust_matrix[n_a][n_b] = 10
    allowed, reason = engine.can_trade(n_a, n_b)
    assert not allowed
    assert "hostile" in reason


def test_attack_rules():
    """Test adjacency requirements for attacks."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    engine = ActionEngine(world)
    
    n_a = list(world.nations.keys())[0]
    
    # Find a border province
    border_provs = engine.spatial.get_border_provinces(n_a)
    if not border_provs:
        pytest.skip("Nation has no borders, cannot test attack")
        
    my_border = border_provs[0]
    
    # Find the enemy neighbor
    target_id = None
    for n in world.provinces[my_border].neighbors:
        if n in world.provinces:
            if world.provinces[n].owner_id != n_a and world.provinces[n].owner_id is not None:
                target_id = n
                break
            
    if target_id:
        allowed, _ = engine.can_attack(n_a, target_id)
        assert allowed


def test_execution_waterfall():
    """Test that defense actions are executed in priority order with proper resource validation."""
    world = generate_world(seed=42, n_cells=50, n_nations=1)
    engine = ActionEngine(world)
    nation_id = list(world.nations.keys())[0]
    
    # Setup: Limited resources to test affordability
    # SOLDIER costs: 5 budget, 2 materials, 0 energy, 1 population
    # We set up to afford 2 units but not 3
    world.nations[nation_id].total_budget = 12.0  # Enough for 2 (10) but not 3 (15)
    world.nations[nation_id].total_materials = 10.0  # Enough for all
    world.nations[nation_id].total_energy = 10.0
    world.nations[nation_id].total_workers = 10  # Enough for all
    
    # Create 3 CREATE_UNIT actions with explicit unit_type
    payload = DefensePayload(
        decision=Decision.APPROVE,
        moves=[
            DefenseActionItem(
                priority=1, 
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "SOLDIER", "quantity": 1}
            ),
            DefenseActionItem(
                priority=2, 
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "SOLDIER", "quantity": 1}
            ),
            DefenseActionItem(
                priority=3, 
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "SOLDIER", "quantity": 1}
            )
        ]
    )
    
    # Mock Envelope using conftest helper
    envelope = create_test_envelope(
        nation_id,
        defense_payload=payload,
        defense_public_intent=DefenseIntentType.CONQUEST,
        defense_private_intent=DefenseIntentType.CONQUEST,
    )
    
    logs = engine.execute_envelope(envelope)
    
    # Verify State: 2 units created (2 * 5 = 10), remaining 2 budget
    assert world.nations[nation_id].total_budget == 2.0
    # Materials: 10 - (2 * 2) = 6
    assert world.nations[nation_id].total_materials == 6.0
    
    # Verify Logs: 2 created, 1 failed
    created_count = sum(1 for l in logs if "Created" in l)
    failed_count = sum(1 for l in logs if "failed" in l)
    assert created_count == 2
    assert failed_count == 1
