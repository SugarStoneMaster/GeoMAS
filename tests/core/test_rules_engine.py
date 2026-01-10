import pytest
import sys
import os

# Add project root to path (Two levels up)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.world.map_engine import generate_world
from geomas.core.rules_engine import ActionEngine
from geomas.schemas.world import ResourceBundle
from geomas.schemas.actions import ActionType, MilitaryPayload, MilitaryActionItem, DecisionSource
from geomas.schemas.protocol import CountryEnvelope, GlobalStrategy, PublicIntent, MilitaryIntent, MilitaryIntentType, EconomicPayload, EconomicIntent, EconomicIntentType, ForeignPayload, ForeignIntent, ForeignIntentType

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
    
    # Set budget
    world.nations[nation_id].internal_state.budget = 100.0
    
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
    
    # Case 1: High Trust
    world.trust_matrix[n_a][n_b] = 0.8
    allowed, _ = engine.can_trade(n_a, n_b)
    assert allowed
    
    # Case 2: Low Trust (War)
    world.trust_matrix[n_a][n_b] = 0.1
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
    """Test that military actions are executed in priority order until budget runs out."""
    world = generate_world(seed=42, n_cells=50, n_nations=1)
    engine = ActionEngine(world)
    nation_id = list(world.nations.keys())[0]
    
    # Setup: Budget = 150
    world.nations[nation_id].internal_state.budget = 150.0
    initial_readiness = world.nations[nation_id].internal_state.military_readiness
    
    # Costs: MOBILIZE=100, FORTIFY=50
    # We try 3 actions:
    # 1. Mobilize (100) -> OK (Rem: 50)
    # 2. Fortify (50) -> OK (Rem: 0)
    # 3. Mobilize (100) -> FAIL (Insufficient)
    
    payload = MilitaryPayload(
        source=DecisionSource.MINISTRY_ADVICE,
        moves=[
            MilitaryActionItem(priority=1, action_type=ActionType.MOBILIZE_UNIT),
            MilitaryActionItem(priority=2, action_type=ActionType.FORTIFY_PROVINCE),
            MilitaryActionItem(priority=3, action_type=ActionType.MOBILIZE_UNIT)
        ]
    )
    
    # Mock Envelope
    envelope = CountryEnvelope(
        turn=1, sender_id=nation_id, global_strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
        public_statement="", public_intent=PublicIntent.AGGRESSIVE,
        military_payload=payload, military_intent=MilitaryIntent(type=MilitaryIntentType.CONQUEST, reasoning=""),
        economic_payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE),
        economic_intent=EconomicIntent(type=EconomicIntentType.IDLE, reasoning=""),
        foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
        foreign_intent=ForeignIntent(type=ForeignIntentType.IDLE, reasoning="")
    )
    
    logs = engine.execute_envelope(envelope)
    
    # Verify State
    assert world.nations[nation_id].internal_state.budget == 0.0
    assert world.nations[nation_id].internal_state.military_readiness > initial_readiness
    
    # Verify Logs
    assert any("Mobilized" in l for l in logs)
    assert any("Fortified" in l for l in logs)
    assert any("Skipped" in l for l in logs) # The 3rd action should be skipped
