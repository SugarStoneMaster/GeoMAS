
import pytest
from geomas.agents.context.military import MilitaryTranslator
from geomas.world.generation.generator import generate_world
from geomas.actions.defense.schemas import UnitType


def test_logistics_clamping():
    """Verify that the intent-based strategic options section is present and not excessively long."""
    world = generate_world(seed=42, n_cells=300, n_nations=3)

    translator = MilitaryTranslator(world)
    nation_id = list(world.nations.keys())[0]

    # 1. Generate report
    report = translator.generate_military_report(nation_id)

    print("\n\n--- REPORT START ---\n")
    print(report)
    print("\n--- REPORT END ---\n")

    # 2. Check for the new intent-based section header
    assert "## STRATEGIC OPTIONS" in report

    # 3. Count MOVE_TROOPS JSON hints — should not be overwhelming
    move_count = report.count("MOVE_TROOPS source=")
    print(f"Move hint count: {move_count}")

    # The intent-based prompt caps each block: 3 attack targets/enemy, 4 support, 4 reinforce, 3 expand
    # Plus 3 naval + 3 air = well under 30 total hints
    assert move_count <= 30, f"Too many move hints presented: {move_count}"

    # 4. Check at least one intent block is present
    has_intent_block = any(
        marker in report
        for marker in ["⚔️ OFFENSIVE", "🛡️ SUPPORT", "🏰 REINFORCE", "🌍 EXPANSION", "No military moves available"]
    )
    assert has_intent_block


def test_move_scoring_logic():
    """Verify that strategic moves are prioritized."""
    # Integration test via the translator — placeholder for future scoring assertions
    pass
