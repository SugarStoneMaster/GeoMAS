"""
Tests for Nation Profile Generator.
"""

import pytest
from geomas.world import generate_world
from geomas.agents.context import NationProfileGenerator, SpatialTranslator
from geomas.agents.schemas import GlobalStrategy


@pytest.fixture
def world():
    """Create a test world."""
    return generate_world(seed=42, history_seed=99, n_cells=200, n_nations=4)


class TestNationProfileGenerator:
    """Tests for NationProfileGenerator class."""
    
    def test_create_generator(self, world):
        """Can create a profile generator."""
        generator = NationProfileGenerator(world)
        assert generator is not None
        assert generator.world == world
    
    def test_generate_profile_contains_identity(self, world):
        """Profile includes nation identity section."""
        generator = NationProfileGenerator(world)
        nation_id = list(world.nations.keys())[0]
        
        profile = generator.generate_profile(
            nation_id=nation_id,
            strategy=GlobalStrategy.COALITION_BUILDER
        )
        
        assert "NATION IDENTITY" in profile
        assert world.nations[nation_id].name in profile
        assert "Coalition Builder" in profile
    
    def test_generate_profile_contains_geography(self, world):
        """Profile includes geographic intelligence."""
        generator = NationProfileGenerator(world)
        nation_id = list(world.nations.keys())[0]
        
        profile = generator.generate_profile(
            nation_id=nation_id,
            strategy=GlobalStrategy.ARMED_ISOLATIONISM
        )
        
        assert "GEOGRAPHY" in profile
        assert "BORDERS" in profile or "isolated" in profile.lower()
    
    def test_generate_profile_contains_relationships(self, world):
        """Profile includes relationship summary."""
        generator = NationProfileGenerator(world)
        nation_id = list(world.nations.keys())[0]
        
        profile = generator.generate_profile(
            nation_id=nation_id,
            strategy=GlobalStrategy.TOTAL_EXPANSIONISM
        )
        
        assert "RELATIONSHIPS" in profile
    
    def test_generate_profile_contains_economy(self, world):
        """Profile includes economic position."""
        generator = NationProfileGenerator(world)
        nation_id = list(world.nations.keys())[0]
        
        profile = generator.generate_profile(
            nation_id=nation_id,
            strategy=GlobalStrategy.MERCANTILE_HEGEMONY
        )
        
        assert "ECONOMIC POSITION" in profile
        assert "provinces" in profile.lower()
    
    def test_all_strategies_have_description(self, world):
        """All GlobalStrategy values have archetype descriptions."""
        generator = NationProfileGenerator(world)
        nation_id = list(world.nations.keys())[0]
        
        for strategy in GlobalStrategy:
            profile = generator.generate_profile(nation_id=nation_id, strategy=strategy)
            assert len(profile) > 100  # Reasonable profile length
    
    def test_invalid_nation_returns_error(self, world):
        """Invalid nation ID returns error message."""
        generator = NationProfileGenerator(world)
        
        profile = generator.generate_profile(
            nation_id="nonexistent_nation",
            strategy=GlobalStrategy.COALITION_BUILDER
        )
        
        assert "Error" in profile
    
    def test_profile_without_genesis_db(self, world):
        """Profile works without genesis DB."""
        generator = NationProfileGenerator(world, genesis_db=None)
        nation_id = list(world.nations.keys())[0]
        
        profile = generator.generate_profile(
            nation_id=nation_id,
            strategy=GlobalStrategy.COALITION_BUILDER,
            include_genesis=True
        )
        
        # Should still generate profile without historical section
        assert "NATION IDENTITY" in profile
        assert "RELATIONSHIPS" in profile


class TestIntegrationWithSpatialTranslator:
    """Test integration between NationProfileGenerator and SpatialTranslator."""
    
    def test_profile_includes_spatial_report(self, world):
        """Profile generator uses SpatialTranslator output."""
        generator = NationProfileGenerator(world)
        nation_id = list(world.nations.keys())[0]
        
        # Generate standalone spatial report
        translator = SpatialTranslator(world)
        spatial_report = translator.generate_intelligence_report(nation_id)
        
        # Generate full profile
        profile = generator.generate_profile(nation_id, GlobalStrategy.COALITION_BUILDER)
        
        # Spatial report content should be in profile
        assert "GEOGRAPHY" in profile
        assert "BORDERS" in profile or "RESOURCES" in profile
