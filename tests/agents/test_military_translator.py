"""
Tests for Military Translator.
"""

import pytest
from geomas.world import generate_world
from geomas.agents.context import MilitaryTranslator


@pytest.fixture
def world():
    """Create a test world with some military units."""
    world = generate_world(seed=42, history_seed=99, n_cells=200, n_nations=4)
    
    # Add some troops to make tests meaningful
    for nation_id, nation in world.nations.items():
        if nation.province_ids:
            # Put troops in first few provinces
            for i, p_id in enumerate(nation.province_ids[:3]):
                world.provinces[p_id].soldiers = 100 + i * 50
                world.provinces[p_id].aircraft = 20 + i * 10
            
            # Update nation totals
            nation.total_soldiers = sum(world.provinces[p].soldiers for p in nation.province_ids)
            nation.total_aircraft = sum(world.provinces[p].aircraft for p in nation.province_ids)
    
    return world


class TestMilitaryTranslator:
    """Tests for MilitaryTranslator class."""
    
    def test_create_translator(self, world):
        """Can create a military translator."""
        translator = MilitaryTranslator(world)
        assert translator is not None
        assert translator.world == world
    
    def test_generate_report_contains_overview(self, world):
        """Report includes military overview section."""
        translator = MilitaryTranslator(world)
        nation_id = list(world.nations.keys())[0]
        
        report = translator.generate_military_report(nation_id)
        
        assert "MILITARY OVERVIEW" in report
        assert "soldiers" in report.lower() or "ground forces" in report.lower()
    
    def test_generate_report_contains_deployment(self, world):
        """Report includes deployment status."""
        translator = MilitaryTranslator(world)
        nation_id = list(world.nations.keys())[0]
        
        report = translator.generate_military_report(nation_id)
        
        assert "DEPLOYMENT" in report
    
    def test_generate_report_contains_border_defense(self, world):
        """Report includes border defense analysis for nations with neighbors."""
        translator = MilitaryTranslator(world)
        
        # Find a nation with neighbors
        for nation_id in world.nations.keys():
            neighbors = translator.spatial.get_neighboring_nations(nation_id)
            if neighbors:
                report = translator.generate_military_report(nation_id)
                assert "BORDER DEFENSE" in report
                break
    
    def test_invalid_nation_returns_error(self, world):
        """Invalid nation ID returns error message."""
        translator = MilitaryTranslator(world)
        
        report = translator.generate_military_report("nonexistent_nation")
        
        assert "Error" in report
    
    def test_nuclear_status_shown(self, world):
        """Nuclear arsenal is reported when present."""
        translator = MilitaryTranslator(world)
        nation_id = list(world.nations.keys())[0]
        
        # Give nation nukes
        world.nations[nation_id].nukes = 5
        
        report = translator.generate_military_report(nation_id)
        
        assert "NUCLEAR" in report
        assert "5" in report
    
    def test_undefended_borders_warning(self, world):
        """Warning shown for undefended border provinces."""
        translator = MilitaryTranslator(world)
        nation_id = list(world.nations.keys())[0]
        
        # Remove all troops from border provinces
        border_provs = translator.spatial.get_border_provinces(nation_id)
        for p_id in border_provs:
            world.provinces[p_id].soldiers = 0
            world.provinces[p_id].aircraft = 0
        
        report = translator.generate_military_report(nation_id)
        
        # Should warn about undefended borders
        assert "UNDEFENDED" in report or "no troops" in report.lower()


class TestMilitaryOptions:
    """Tests for attack options and reinforcement logic."""
    
    def test_attack_options_identified(self, world):
        """Attack options shown when we have advantage."""
        translator = MilitaryTranslator(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Give us overwhelming force on a border province
        border_provs = translator.spatial.get_border_provinces(nation_id)
        if border_provs:
            world.provinces[border_provs[0]].soldiers = 500
            world.provinces[border_provs[0]].aircraft = 100
            
            # Make sure enemy has fewer troops
            for n_id in world.provinces[border_provs[0]].neighbors:
                neighbor_prov = world.provinces.get(n_id)
                if neighbor_prov and neighbor_prov.owner_id and neighbor_prov.owner_id != nation_id:
                    neighbor_prov.soldiers = 50
                    neighbor_prov.aircraft = 10
        
        report = translator.generate_military_report(nation_id)
        
        # Should identify attack options
        assert "ATTACK OPTIONS" in report or "advantage" in report.lower()


class TestForceRatios:
    """Tests for force ratio calculations."""
    
    def test_superior_strength_identified(self, world):
        """Superior military strength is correctly identified."""
        translator = MilitaryTranslator(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Make this nation much stronger
        nation.total_soldiers = 10000
        nation.total_aircraft = 1000
        nation.total_navy = 500
        
        # Make neighbors weaker
        neighbors = translator.spatial.get_neighboring_nations(nation_id)
        for n_id in neighbors:
            world.nations[n_id].total_soldiers = 1000
            world.nations[n_id].total_aircraft = 100
            world.nations[n_id].total_navy = 50
        
        report = translator.generate_military_report(nation_id)
        
        assert "superior" in report.lower() or "advantage" in report.lower()
