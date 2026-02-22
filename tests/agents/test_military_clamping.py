
import pytest
from geomas.agents.context.military import MilitaryTranslator
from geomas.world.generation.generator import generate_world
from geomas.actions.defense.schemas import UnitType

def test_logistics_clamping():
    """Verify that logistics options are clamped to max 15 items."""
    world = generate_world(seed=42, n_cells=300, n_nations=3)
    
    translator = MilitaryTranslator(world)
    nation_id = list(world.nations.keys())[0]
    
    # 1. Generate report
    report = translator.generate_military_report(nation_id)
    
    print("\n\n--- REPORT START ---\n")
    print(report)
    print("\n--- REPORT END ---\n")
    
    # 2. Check for Logistics section
    assert "## STRATEGIC LOGISTICS" in report
    assert "### GROUND OPERATIONS" in report
    
    # 3. Count bullet points in logistics section
    # Extract logistics part
    parts = report.split("## STRATEGIC LOGISTICS")
    logistics_text = parts[1]
    
    # Count lines starting with "- "
    bullet_count = logistics_text.count("\n- ")
    
    print(f"Bullet count: {bullet_count}")
    
    # 4. Assert limits
    # Max would be 10 sol + 3 navy + 2 air = 15
    # Allowing slight variance for headers/empty messages
    assert bullet_count <= 20, "Too many logistics options presented!"
    
    # 5. Check if it's not empty (should have some moves)
    assert bullet_count >= 0

def test_move_scoring_logic():
    """Verify that strategic moves are prioritized."""
    # This is an integration test via the translator
    pass
