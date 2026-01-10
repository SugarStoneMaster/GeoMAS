import pytest
import sys
import os

# Add project root to path (Two levels up)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.world.map_engine import generate_world
from geomas.core.rules_engine import ActionValidator
from geomas.schemas.world import ResourceBundle # Updated import

def test_movement_rules():
    """Test topological movement constraints."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    validator = ActionValidator(world)
    
    nation_id = list(world.nations.keys())[0]
    my_provinces = world.nations[nation_id].province_ids
    
    # 1. Valid Move (Internal)
    # Find two connected provinces owned by nation
    p1 = my_provinces[0]
    p2 = None
    for n in world.provinces[p1].neighbors:
        if n in world.provinces and n in my_provinces: # Check existence
            p2 = n
            break
            
    if p2:
        allowed, reason = validator.can_move_troops(nation_id, p1, p2)
        assert allowed, f"Should allow internal move: {reason}"
    
    # 2. Invalid Move (To Enemy)
    enemy_id = list(world.nations.keys())[1]
    enemy_prov = world.nations[enemy_id].province_ids[0]
    
    allowed, reason = validator.can_move_troops(nation_id, p1, enemy_prov)
    assert not allowed
    assert "foreign" in reason or "ATTACK" in reason

def test_economic_rules():
    """Test budget constraints."""
    world = generate_world(seed=42, n_cells=50, n_nations=1)
    validator = ActionValidator(world)
    nation_id = list(world.nations.keys())[0]
    
    # Set budget
    world.nations[nation_id].internal_state.budget = 100.0
    
    # Affordable
    allowed, _ = validator.can_afford_budget(nation_id, 50.0)
    assert allowed
    
    # Too expensive
    allowed, reason = validator.can_afford_budget(nation_id, 150.0)
    assert not allowed
    assert "Insufficient" in reason

def test_diplomatic_rules():
    """Test trade constraints based on trust."""
    world = generate_world(seed=42, n_cells=50, n_nations=2)
    validator = ActionValidator(world)
    
    n_a = list(world.nations.keys())[0]
    n_b = list(world.nations.keys())[1]
    
    # Case 1: High Trust
    world.trust_matrix[n_a][n_b] = 0.8
    allowed, _ = validator.can_trade(n_a, n_b)
    assert allowed
    
    # Case 2: Low Trust (War)
    world.trust_matrix[n_a][n_b] = 0.1
    allowed, reason = validator.can_trade(n_a, n_b)
    assert not allowed
    assert "hostile" in reason

def test_attack_rules():
    """Test adjacency requirements for attacks."""
    world = generate_world(seed=42, n_cells=100, n_nations=2)
    validator = ActionValidator(world)
    
    n_a = list(world.nations.keys())[0]
    
    # Find a border province
    border_provs = validator.spatial.get_border_provinces(n_a)
    if not border_provs:
        pytest.skip("Nation has no borders, cannot test attack")
        
    my_border = border_provs[0]
    
    # Find the enemy neighbor
    target_id = None
    for n in world.provinces[my_border].neighbors:
        # FIX: Check if neighbor exists in world.provinces
        if n in world.provinces:
            if world.provinces[n].owner_id != n_a and world.provinces[n].owner_id is not None:
                target_id = n
                break
            
    if target_id:
        allowed, _ = validator.can_attack(n_a, target_id)
        assert allowed
