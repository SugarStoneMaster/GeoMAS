import pytest
from geomas.world import generate_world
from geomas.schemas.world import RelationshipState
from geomas.agents.context.input import ForeignInputBuilder, DefenseInputBuilder, PresidentInputBuilder

def test_global_alliance_visibility():
    """Verify that Nations see each other's alliances without duplication."""
    # 1. Setup world with 3 nations
    world = generate_world(seed=42, history_seed=99, n_cells=100, n_nations=3)
    sorted_ids = sorted(world.nations.keys())
    nation_a = sorted_ids[0]
    nation_b = sorted_ids[1]
    nation_c = sorted_ids[2]
    
    # 2. Forge alliance between A and B
    world.relationship_matrix[nation_a][nation_b] = RelationshipState.MUTUAL_DEFENSE
    world.relationship_matrix[nation_b][nation_a] = RelationshipState.MUTUAL_DEFENSE
    
    # builders
    foreign_builder = ForeignInputBuilder(world)
    defense_builder = DefenseInputBuilder(world)
    president_builder = PresidentInputBuilder(world)
    
    # Sanitized names for assertion
    from geomas.agents.context.input.base import BaseInputBuilder
    base = BaseInputBuilder(world)
    name_a = base._sanitize_prompt(world.nations[nation_a].name)
    name_b = base._sanitize_prompt(world.nations[nation_b].name)
    
    # 3. Check Nation C's prompt
    prompts = [
        foreign_builder.build(nation_c, turn=1),
        defense_builder.build(nation_c, turn=1),
        president_builder.build(nation_c, turn=1)
    ]
    
    for prompt in prompts:
        # A. Verify Treaty Network section exists and contains A-B alliance
        assert "### GLOBAL TREATY NETWORK (Third-Party Alliances)" in prompt
        assert name_a in prompt
        assert name_b in prompt
        assert "MUTUAL_DEFENSE" in prompt
        
        # B. Verify it is NOT in the "Other nations" section (preventing duplication)
        other_nations_section = prompt.split("## Other nations")[1]
        assert "Treaties:" not in other_nations_section

def test_no_self_in_global_network():
    """Verify that a nation's own treaties are not listed in the global network section."""
    world = generate_world(seed=42, history_seed=99, n_cells=100, n_nations=3)
    sorted_ids = sorted(world.nations.keys())
    nation_a = sorted_ids[0]
    nation_b = sorted_ids[1]
    
    # Alliance A-B
    world.relationship_matrix[nation_a][nation_b] = RelationshipState.MUTUAL_DEFENSE
    world.relationship_matrix[nation_b][nation_a] = RelationshipState.MUTUAL_DEFENSE
    
    foreign_builder = ForeignInputBuilder(world)
    
    # Check Nation A's prompt
    prompt_a = foreign_builder.build(nation_a, turn=1)
    
    # A-B treaty should be in the primary section, not in global network
    # In primary it looks like: - **NationB** (B): MUTUAL_DEFENSE
    # In global network it would look like: - **NationA** & **NationB**: MUTUAL_DEFENSE
    
    # If there are NO other alliances, the global section should be missing entirely
    assert "### GLOBAL TREATY NETWORK" not in prompt_a

if __name__ == "__main__":
    pytest.main([__file__])
