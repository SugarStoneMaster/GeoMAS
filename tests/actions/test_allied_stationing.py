
import pytest
from geomas.actions.engine import ActionEngine
from geomas.world.generation.generator import generate_world
from geomas.actions.defense.schemas import DefensePayload, DefenseActionType, DefenseActionItem, UnitType
from geomas.actions.defense.handler import execute_defense_waterfall
from geomas.schemas.world import RelationshipState, ProvinceState, NationState, TerrainType

@pytest.fixture
def engine():
    # minimalist world
    world = generate_world(seed=42, n_cells=10, n_nations=1) 
    return ActionEngine(world)

def setup_scenario(engine):
    """
    Setup linear map: [P1 (A)] -- [P2 (B)] -- [P3 (C)]
    Relation: A & B are Allies (Mutual Defense)
    """
    world = engine.world
    world.nations.clear()
    world.provinces.clear()
    
    # Create Nations
    world.nations["A"] = NationState(id="A", name="Nation A", color="#FF0000", total_energy=1000)
    world.nations["B"] = NationState(id="B", name="Nation B", color="#00FF00", total_energy=1000)
    world.nations["C"] = NationState(id="C", name="Nation C", color="#0000FF", total_energy=1000)
    
    # Create Provinces
    p1 = ProvinceState(id=1, owner_id="A", terrain=TerrainType.LAND, coordinates=(0,0), neighbors=[2], soldiers=100)
    p2 = ProvinceState(id=2, owner_id="B", terrain=TerrainType.LAND, coordinates=(1,0), neighbors=[1, 3], soldiers=10) # B has few troops
    p3 = ProvinceState(id=3, owner_id="C", terrain=TerrainType.LAND, coordinates=(2,0), neighbors=[2], soldiers=50)
    
    world.provinces = {1: p1, 2: p2, 3: p3}
    world.nations["A"].province_ids = [1]
    world.nations["B"].province_ids = [2]
    world.nations["C"].province_ids = [3]
    
    # Rebuild graph
    engine.spatial._build_graph()
    
    # Set Relations: A-B are Allies
    world.relationship_matrix = {
        "A": {"B": RelationshipState.MUTUAL_DEFENSE, "C": RelationshipState.WAR},
        "B": {"A": RelationshipState.MUTUAL_DEFENSE},
        "C": {"A": RelationshipState.WAR}
    }
    
    return world

def test_guest_troops_stationing(engine):
    world = setup_scenario(engine)
    
    # 1. Move A troops (50) to B (P2)
    move_payload = DefensePayload(
        moves=[DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.SOLDIER,
            quantity=50,
            source_province_id=1,
            target_province_id=2 # Allied
        )]
    )
    
    execute_defense_waterfall(engine, "A", move_payload)
    
    # CHECK 1: Move Success
    assert move_payload.moves[0].execution_outcome.status == "SUCCESS"
    
    # CHECK 2: Troops are GUESTS in P2
    p2 = world.provinces[2]
    assert p2.owner_id == "B" # Owner unchanged
    assert p2.soldiers == 10  # B's troops unchanged
    assert p2.guest_troops["A"]["soldiers"] == 50 # A's troops are guests
    
    # CHECK 3: Relations still MUTUAL_DEFENSE (No War trigger)
    assert world.relationship_matrix["A"]["B"] == RelationshipState.MUTUAL_DEFENSE


def test_guest_troops_moving_out(engine):
    world = setup_scenario(engine)
    
    # Setup: Pre-place guest troops
    p2 = world.provinces[2]
    p2.guest_troops = {"A": {"soldiers": 50, "aircraft": 0}}
    
    # Action: Move Guest Troops from P2 (Allied) to P3 (Enemy C)
    # Source ID is P2 (where they guest)
    attack_payload = DefensePayload(
        moves=[DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.SOLDIER,
            quantity=100, # Overwhelming force to ensure win
            source_province_id=2, # Moving FROM Allied land
            target_province_id=3  # To Enemy
        )]
    )
    
    # Needs to have guest troops there first!
    p2.guest_troops["A"]["soldiers"] = 100
    
    execute_defense_waterfall(engine, "A", attack_payload)
    
    result = attack_payload.moves[0].execution_outcome
    
    # CHECK 1: Success
    assert result.status == "SUCCESS", f"Failed: {result.reason}"
    
    # CHECK 2: Guests removed from P2
    assert "A" not in p2.guest_troops or p2.guest_troops["A"].get("soldiers", 0) == 0
    
    # CHECK 3: Combat happened at P3 (50 attackers vs 50 defenders) -> likely mutual destruction or close
    # Just check that P3 changed or troops reduced
    p3 = world.provinces[3]
    # Simple check: Action didn't error. Combat logic is tested elsewhere.
    assert p3.soldiers != 50 or p3.owner_id == "A" # Combat occurred
