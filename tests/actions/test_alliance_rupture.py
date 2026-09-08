"""
Test for Alliance Rupture on Attack.
Verifies that attacking an ally (MUTUAL_DEFENSE or NON_AGGRESSION) immediately sets relationship to WAR.
"""
import pytest
from geomas.schemas.world import WorldState, NationState, RelationshipState, ProvinceState, TerrainType
from geomas.actions import ActionEngine
from geomas.actions.defense.handler import execute_defense_waterfall
from geomas.actions.defense.schemas import DefensePayload, DefenseActionItem, DefenseActionType, UnitType

@pytest.fixture
def engine():
    w = WorldState(turn=1)
    
    # Nations
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue", total_energy=1000, total_soldiers=100, nukes=5)
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red", total_energy=1000, total_soldiers=100)
    
    # Provinces
    # 1: A (Source)
    w.provinces[1] = ProvinceState(id=1, owner_id="NAT_A", terrain=TerrainType.LAND, soldiers=50, coordinates=(0.0, 0.0))
    # 2: B (Target - Neighbor)
    w.provinces[2] = ProvinceState(id=2, owner_id="NAT_B", terrain=TerrainType.LAND, soldiers=10, neighbors=[1], coordinates=(1.0, 0.0))
    w.provinces[1].neighbors = [2]
    
    # Init Matrices
    for n1 in w.nations:
        w.relationship_matrix[n1] = {}
        w.trust_matrix[n1] = {}
        for n2 in w.nations:
            w.relationship_matrix[n1][n2] = RelationshipState.PEACE
            w.trust_matrix[n1][n2] = 50.0
            
    engine = ActionEngine(w)
    return engine

def test_move_troops_into_ally_is_stationing(engine):
    """
    Verify that moving troops into allied territory is treated as Friendly Stationing (Guest Troops),
    NOT an attack, and does NOT break the alliance.
    """
    w = engine.world
    
    # 1. Setup Alliance
    w.relationship_matrix["NAT_A"]["NAT_B"] = RelationshipState.MUTUAL_DEFENSE
    w.relationship_matrix["NAT_B"]["NAT_A"] = RelationshipState.MUTUAL_DEFENSE
    w.trust_matrix["NAT_A"]["NAT_B"] = 90.0
    w.trust_matrix["NAT_B"]["NAT_A"] = 90.0
    
    # 2. Execute Move (A -> B)
    payload = DefensePayload(moves=[
        DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.SOLDIER,
            source_province_id=1,
            target_province_id=2,
            quantity=20, 
            target_nation_id="NAT_B"
        )
    ])
    
    execute_defense_waterfall(engine, "NAT_A", payload)
    
    # 3. Assertions
    # Relationship should REMAIN MUTUAL_DEFENSE (No War)
    assert w.relationship_matrix["NAT_A"]["NAT_B"] == RelationshipState.MUTUAL_DEFENSE
    
    # Trust should NOT be penalized
    assert w.trust_matrix["NAT_B"]["NAT_A"] == 90.0
    
    # Troops should be stationed as GUESTS
    target_prov = w.provinces[2]
    assert target_prov.owner_id == "NAT_B"
    assert target_prov.guest_troops["NAT_A"]["soldiers"] == 20
    
    # No combat log
    assert not any("conquered by NAT_A" in log for log in engine.logs)

def test_nuke_breaks_alliance(engine):
    w = engine.world
    
    # 1. Setup Non-Aggression
    w.relationship_matrix["NAT_A"]["NAT_B"] = RelationshipState.NON_AGGRESSION
    w.relationship_matrix["NAT_B"]["NAT_A"] = RelationshipState.NON_AGGRESSION
    
    # 2. Execute Nuke
    payload = DefensePayload(moves=[
        DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.NUCLEAR_OPTION,
            target_province_id=2, # B's province
            quantity=1,
            target_nation_id="NAT_B"
        )
    ])
    
    execute_defense_waterfall(engine, "NAT_A", payload)
    
    # 3. Assertions
    # Relationship -> WAR
    assert w.relationship_matrix["NAT_A"]["NAT_B"] == RelationshipState.WAR
    
    # Trust -> 0 (Nuke sets explicit 0)
    assert w.trust_matrix["NAT_B"]["NAT_A"] == 0
    
    # Log check
    assert any("BROKE ALLIANCE by nuking" in log for log in engine.logs)
