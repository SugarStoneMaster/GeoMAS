import pytest
from geomas.schemas.world import WorldState, NationState, RelationshipState, ProvinceState, TerrainType, WarStats
from geomas.simulation.engine import SimulationEngine
from geomas.actions import ActionEngine
from geomas.actions.defense.handler import execute_defense_waterfall
from geomas.actions.defense.schemas import DefensePayload, DefenseActionItem, DefenseActionType, UnitType
from geomas.actions.common import Decision

@pytest.fixture
def base_sim():
    # Setup: A (Attacker), B (Target Province Owner), C (Guest in B)
    w = WorldState(turn=1)
    
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Attacker A", color="blue", total_aircraft=100, total_energy=1000)
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Target B", color="red")
    w.nations["NAT_C"] = NationState(id="NAT_C", name="Guest C", color="green", total_aircraft=50)
    
    # Provinces
    # 1: A (Source)
    w.provinces[1] = ProvinceState(id=1, owner_id="NAT_A", terrain=TerrainType.LAND, aircraft=50, coordinates=(0,0))
    # 2: B (Target)
    w.provinces[2] = ProvinceState(id=2, owner_id="NAT_B", terrain=TerrainType.LAND, coordinates=(1,0), neighbors=[1])
    w.provinces[1].neighbors = [2]
    
    # C is Guest in B
    w.provinces[2].guest_troops["NAT_C"] = {"soldiers": 0, "aircraft": 20, "navy": 0}
    
    # Relationships
    for n in ["NAT_A", "NAT_B", "NAT_C"]:
        w.relationship_matrix[n] = {other: RelationshipState.PEACE for other in ["NAT_A", "NAT_B", "NAT_C"] if other != n}
        w.trust_matrix[n] = {other: 50.0 for other in ["NAT_A", "NAT_B", "NAT_C"] if other != n}
        
    sim = SimulationEngine(n_nations=3, map_seed=1, history_seed=1)
    sim.world = w
    sim.engine = ActionEngine(w)
    sim.agents = {"NAT_A": None, "NAT_B": None, "NAT_C": None}
    
    return sim

def test_air_strike_hits_guest_triggers_war(base_sim):
    sim = base_sim
    w = sim.world
    
    payload = DefensePayload(moves=[
        DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS, # Move with aircraft = strike
            unit_type=UnitType.AIRCRAFT,
            source_province_id=1,
            target_province_id=2,
            quantity=30,
            target_nation_id="NAT_B"
        )
    ])
    
    execute_defense_waterfall(sim.engine, "NAT_A", payload)
    
    # 1. A and B are at WAR
    assert w.relationship_matrix["NAT_A"]["NAT_B"] == RelationshipState.WAR
    
    # 2. A and C are at WAR (because C's guest troops were hit)
    assert w.relationship_matrix["NAT_A"]["NAT_C"] == RelationshipState.WAR
    # Standardized log for initial aggression: "started WAR with {id} by aggression"
    assert any("started WAR with NAT_C by aggression" in l for l in sim.engine.logs)
    
    # 3. Guest units are destroyed
    assert w.provinces[2].guest_troops == {}
    assert w.nations["NAT_C"].total_aircraft == 30 # 50 - 20

def test_naval_landing_hits_guest_navy_triggers_war():
    # Setup for Naval: A attacks water province 2 (owned by B, with C's guest navy inside).
    # Province 10 is A's OCEAN territorial water where A's navy is deployed.
    w = WorldState(turn=1)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="A", color="blue", total_navy=10, total_energy=1000)
    w.nations["NAT_B"] = NationState(id="NAT_B", name="B", color="red")
    w.nations["NAT_C"] = NationState(id="NAT_C", name="C", color="green", total_navy=5)

    # Province 10: A's home ocean cell (source)
    w.provinces[10] = ProvinceState(id=10, owner_id="NAT_A", terrain=TerrainType.OCEAN, navy=10, coordinates=(0,0), neighbors=[2])
    # Province 2: B's territorial water (target) — C has guest navy here
    w.provinces[2] = ProvinceState(id=2, owner_id="NAT_B", terrain=TerrainType.OCEAN, coordinates=(1,0), neighbors=[10, 3])
    # Province 3: B's coastal land
    w.provinces[3] = ProvinceState(id=3, owner_id="NAT_B", terrain=TerrainType.COASTAL, coordinates=(2,0), neighbors=[2])

    # FIX: A's navy must start in A's territorial water, not a LAND province.
    w.nations["NAT_A"].territorial_water_ids = [10]
    w.nations["NAT_B"].territorial_water_ids = [2]

    # C has Guest Navy in province 2
    w.provinces[2].guest_troops["NAT_C"] = {"soldiers": 0, "aircraft": 0, "navy": 5}

    # Relationships
    for n in ["NAT_A", "NAT_B", "NAT_C"]:
        w.relationship_matrix[n] = {other: RelationshipState.PEACE for other in ["NAT_A", "NAT_B", "NAT_C"] if other != n}
        w.trust_matrix[n] = {other: 50.0 for other in ["NAT_A", "NAT_B", "NAT_C"] if other != n}

    sim = SimulationEngine(n_nations=3, map_seed=1, history_seed=1)
    sim.world = w
    sim.engine = ActionEngine(w)
    
    # A moves navy from its ocean cell (10) into B's water (2)
    payload = DefensePayload(moves=[
        DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.NAVY,
            source_province_id=10,
            target_province_id=2,
            quantity=10,
            target_nation_id="NAT_B"
        )
    ])
    
    execute_defense_waterfall(sim.engine, "NAT_A", payload)
    
    # A and B are at WAR
    assert w.relationship_matrix["NAT_A"]["NAT_B"] == RelationshipState.WAR
    # A and C are at WAR (because C's guest navy was hit)
    assert w.relationship_matrix["NAT_A"]["NAT_C"] == RelationshipState.WAR
    
    # Guest navy destroyed
    assert w.provinces[2].guest_troops == {}
    assert w.nations["NAT_C"].total_navy == 0

def test_air_strike_betrayal_penalty(base_sim):
    sim = base_sim
    w = sim.world
    
    # A and C are ALLIES
    w.relationship_matrix["NAT_A"]["NAT_C"] = RelationshipState.MUTUAL_DEFENSE
    w.relationship_matrix["NAT_C"]["NAT_A"] = RelationshipState.MUTUAL_DEFENSE
    w.trust_matrix["NAT_C"]["NAT_A"] = 90.0
    
    payload = DefensePayload(moves=[
        DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.AIRCRAFT,
            source_province_id=1,
            target_province_id=2,
            quantity=30,
            target_nation_id="NAT_B"
        )
    ])
    
    execute_defense_waterfall(sim.engine, "NAT_A", payload)
    
    # A and C at WAR
    assert w.relationship_matrix["NAT_A"]["NAT_C"] == RelationshipState.WAR
    # 1. Betrayal Penalty: -50.0
    # 2. Combat Success Penalty: -20.0
    # Total: 90 - 50 - 20 = 20
    assert w.trust_matrix["NAT_C"]["NAT_A"] == 20.0
    assert any("BROKE ALLIANCE" in l for l in sim.engine.logs)
