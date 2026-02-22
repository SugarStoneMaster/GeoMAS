
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from geomas.schemas.world import WorldState, ProvinceState, NationState, TerrainType, RelationshipState
from geomas.agents.context.input.defense import DefenseInputBuilder
from geomas.agents.context.military import MilitaryTranslator


def test_defense_logistics_refinement():
    # 1. Setup World with complex spatial layout
    p1 = ProvinceState(id=1, owner_id="N1", terrain=TerrainType.LAND, coordinates=(0, 0), soldiers=100)
    p2 = ProvinceState(id=2, owner_id="N1", terrain=TerrainType.LAND, coordinates=(1, 1), soldiers=10)  # Interior
    p3 = ProvinceState(id=3, owner_id="N2", terrain=TerrainType.LAND, coordinates=(2, 2), soldiers=50)   # Enemy
    p4 = ProvinceState(id=4, owner_id="N1", terrain=TerrainType.LAND, coordinates=(0, 1), aircraft=5)   # Air base
    ocean = ProvinceState(id=5, owner_id=None, terrain=TerrainType.OCEAN, coordinates=(0, 2))

    # Adjacency: 1-2, 1-3, 1-4, 2-3, 3-4, 4-5
    p1.neighbors = [2, 3, 4]
    p2.neighbors = [1, 3]
    p3.neighbors = [1, 2, 4]
    p4.neighbors = [1, 3, 5]
    ocean.neighbors = [4]

    n1 = NationState(id="N1", name="Nation 1", color="blue", province_ids=[1, 2, 4])
    n2 = NationState(id="N2", name="Nation 2", color="red", province_ids=[3])

    world = WorldState(
        turn=1,
        provinces={1: p1, 2: p2, 3: p3, 4: p4, 5: ocean},
        nations={"N1": n1, "N2": n2},
        trust_matrix={"N1": {"N2": 10.0}},
        relationship_matrix={"N1": {"N2": RelationshipState.WAR}, "N2": {"N1": RelationshipState.WAR}}
    )

    builder = DefenseInputBuilder(world)
    prompt = builder.build("N1", 1)

    print("\n--- GENERATED DEFENSE PROMPT ---")
    print(prompt)

    # Verification: new intent-based section is present
    assert "## STRATEGIC OPTIONS" in prompt

    # Offensive block present (N2 is at WAR, province 3 is adjacent)
    assert "OFFENSIVE OPTIONS" in prompt
    # Province 3 is reachable from province 1 — should appear as MOVE_TROOPS hint
    assert "target=3" in prompt

    # Aircraft should appear (p4 has 5 aircraft and p3 is adjacent)
    assert "AIR STRIKE OPTIONS" in prompt

    # REINFORCE should be present (p4 and p2 are lightly defended borders)
    assert "REINFORCE" in prompt

    print("\nSUCCESS: Intent-based defense prompt verified.")


if __name__ == "__main__":
    test_defense_logistics_refinement()
