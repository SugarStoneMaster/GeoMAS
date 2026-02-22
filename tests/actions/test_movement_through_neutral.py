
import pytest
from geomas.actions.engine import ActionEngine
from geomas.world.generation.generator import generate_world
from geomas.actions.defense.schemas import DefensePayload, DefenseActionType, DefenseActionItem, UnitType
from geomas.actions.defense.handler import execute_defense_waterfall
from geomas.schemas.world import RelationshipState, ProvinceState, NationState, TerrainType

@pytest.fixture
def engine():
    # minimalist world
    world = generate_world(seed=42, n_cells=10, n_nations=1) # Valid generation
    return ActionEngine(world)

def setup_scenario(engine):
    """
    Setup linear map: [P1 (A)] -- [P2 (B)] -- [P3 (C)]
    """
    world = engine.world
    world.nations.clear()
    world.provinces.clear()
    
    # Create Nations
    world.nations["A"] = NationState(id="A", name="Nation A", color="#FF0000", total_energy=1000)
    world.nations["B"] = NationState(id="B", name="Nation B", color="#00FF00", total_energy=1000)
    world.nations["C"] = NationState(id="C", name="Nation C", color="#0000FF", total_energy=1000)
    
    # Create Provinces
    p1 = ProvinceState(id=1, owner_id="A", terrain=TerrainType.LAND, coordinates=(0,0), neighbors=[2], soldiers=10)
    p2 = ProvinceState(id=2, owner_id="B", terrain=TerrainType.LAND, coordinates=(1,0), neighbors=[1, 3], soldiers=0)
    p3 = ProvinceState(id=3, owner_id="C", terrain=TerrainType.LAND, coordinates=(2,0), neighbors=[2], soldiers=0)
    
    world.provinces = {1: p1, 2: p2, 3: p3}
    world.nations["A"].province_ids = [1]
    world.nations["B"].province_ids = [2]
    world.nations["C"].province_ids = [3]
    
    # Rebuild graph
    engine.spatial._build_graph()
    
    return world

def test_cannot_pass_neutral(engine):
    world = setup_scenario(engine)
    
    # Relations: A-B is PEACE (Neutral), A-C is WAR
    world.relationship_matrix = {
        "A": {"B": RelationshipState.PEACE, "C": RelationshipState.WAR},
        "B": {"A": RelationshipState.PEACE},
        "C": {"A": RelationshipState.WAR}
    }
    
    # Action: Move A's troops from P1 to P3 (attacking C), must pass through P2 (B)
    payload = DefensePayload(
        moves=[DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.SOLDIER,
            quantity=5,
            source_province_id=1,
            target_province_id=3
        )]
    )
    
    execute_defense_waterfall(engine, "A", payload)
    
    result = payload.moves[0].execution_outcome
    
    # EXPECTATION: FAILURE because P2 is owned by B (Neutral)
    assert result.status == "FAILED", f"Movement should fail through neutral. Reason: {result.reason}"
    assert "path" in result.reason.lower() or "blocked" in result.reason.lower()

def test_can_pass_ally(engine):
    world = setup_scenario(engine)
    
    # Relations: A-B is ALLIANCE (Mutual Defense), A-C is WAR
    world.relationship_matrix = {
        "A": {"B": RelationshipState.MUTUAL_DEFENSE, "C": RelationshipState.WAR},
        "B": {"A": RelationshipState.MUTUAL_DEFENSE},
        "C": {"A": RelationshipState.WAR}
    }
    
    # Action: Move A from P1 to P3 (through Allied P2)
    payload = DefensePayload(
        moves=[DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.SOLDIER,
            quantity=5,
            source_province_id=1,
            target_province_id=3
        )]
    )
    
    execute_defense_waterfall(engine, "A", payload)
    
    result = payload.moves[0].execution_outcome
    
    # EXPECTATION: SUCCESS because P2 is Allied
    assert result.status == "SUCCESS", f"Movement should succeed through ally. Reason: {result.reason}"


def setup_deep_scenario(engine):
    """
    Setup linear map: [P1 (A)] -- [P2 (B)] -- [P3 (C)] -- [P4 (C)]

    This tests the border-attack guarantee: A can attack P3 (adjacent to allied B),
    but cannot skip through P3 to attack the deeper P4 in a single move.
    """
    world = engine.world
    world.nations.clear()
    world.provinces.clear()

    world.nations["A"] = NationState(id="A", name="Nation A", color="#FF0000", total_energy=1000)
    world.nations["B"] = NationState(id="B", name="Nation B", color="#00FF00", total_energy=1000)
    world.nations["C"] = NationState(id="C", name="Nation C", color="#0000FF", total_energy=1000)

    p1 = ProvinceState(id=1, owner_id="A", terrain=TerrainType.LAND, coordinates=(0, 0), neighbors=[2], soldiers=20)
    p2 = ProvinceState(id=2, owner_id="B", terrain=TerrainType.LAND, coordinates=(1, 0), neighbors=[1, 3], soldiers=0)
    p3 = ProvinceState(id=3, owner_id="C", terrain=TerrainType.LAND, coordinates=(2, 0), neighbors=[2, 4], soldiers=0)
    p4 = ProvinceState(id=4, owner_id="C", terrain=TerrainType.LAND, coordinates=(3, 0), neighbors=[3], soldiers=0)

    world.provinces = {1: p1, 2: p2, 3: p3, 4: p4}
    world.nations["A"].province_ids = [1]
    world.nations["B"].province_ids = [2]
    world.nations["C"].province_ids = [3, 4]

    engine.spatial._build_graph()

    return world


def test_attack_enemy_border_via_ally_succeeds(engine):
    """
    A attacks C's border province (P3) which is directly adjacent to allied B (P2).
    This should succeed: A → B → C_border is a valid attack path.
    """
    world = setup_deep_scenario(engine)

    world.relationship_matrix = {
        "A": {"B": RelationshipState.MUTUAL_DEFENSE, "C": RelationshipState.WAR},
        "B": {"A": RelationshipState.MUTUAL_DEFENSE, "C": RelationshipState.PEACE},
        "C": {"A": RelationshipState.WAR, "B": RelationshipState.PEACE},
    }
    world.trust_matrix = {
        "A": {"B": 80.0, "C": 0.0},
        "B": {"A": 80.0, "C": 50.0},
        "C": {"A": 0.0, "B": 50.0},
    }

    payload = DefensePayload(
        moves=[DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.SOLDIER,
            quantity=10,
            source_province_id=1,
            target_province_id=3,  # C's border province, adjacent to B
        )]
    )

    execute_defense_waterfall(engine, "A", payload)
    result = payload.moves[0].execution_outcome

    # P3 is at C's border with allied B — attack must succeed (path: 1→2→3)
    assert result.status == "SUCCESS", f"Border attack via ally should succeed. Reason: {result.reason}"


def test_attack_deep_enemy_province_blocked(engine):
    """
    A tries to attack C's deep province (P4) without having conquered P3 first.
    P4 is only reachable through P3 (enemy), which is not a permitted intermediate node.
    This must FAIL: troops cannot teleport through unconquered enemy territory.
    """
    world = setup_deep_scenario(engine)

    world.relationship_matrix = {
        "A": {"B": RelationshipState.MUTUAL_DEFENSE, "C": RelationshipState.WAR},
        "B": {"A": RelationshipState.MUTUAL_DEFENSE, "C": RelationshipState.PEACE},
        "C": {"A": RelationshipState.WAR, "B": RelationshipState.PEACE},
    }
    world.trust_matrix = {
        "A": {"B": 80.0, "C": 0.0},
        "B": {"A": 80.0, "C": 50.0},
        "C": {"A": 0.0, "B": 50.0},
    }

    payload = DefensePayload(
        moves=[DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.SOLDIER,
            quantity=10,
            source_province_id=1,
            target_province_id=4,  # C's deep province — only reachable via C's P3
        )]
    )

    execute_defense_waterfall(engine, "A", payload)
    result = payload.moves[0].execution_outcome

    # P4 requires passing through P3 (enemy intermediate node) — must be blocked
    assert result.status == "FAILED", (
        f"Deep attack bypassing enemy territory should fail. Got: {result.status} — {result.reason}"
    )
