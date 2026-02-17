
import pytest
from unittest.mock import MagicMock
from geomas.schemas.world import WorldState, NationState, ProvinceState, RelationshipState, WarStats, TerrainType
from geomas.actions.foreign.handler import _execute_declare_war
from geomas.actions.defense.combat import _conquer_province
from geomas.actions.engine import ActionEngine

def test_war_stats_initialization():
    """Verify WarStats are initialized when war is declared."""
    world = MagicMock(spec=WorldState)
    world.turn = 5
    world.relationship_matrix = {}
    world.trust_matrix = {}
    world.global_events = []
    
    aggressor = MagicMock(spec=NationState)
    aggressor.id = "AGRIA"
    aggressor.province_ids = [1, 2, 3]
    aggressor.active_wars = {}
    
    target = MagicMock(spec=NationState)
    target.id = "VULCANIA"
    target.province_ids = [10, 11]
    target.active_wars = {}
    
    world.nations = {"AGRIA": aggressor, "VULCANIA": target}
    
    engine = MagicMock(spec=ActionEngine)
    engine.world = world
    engine.logs = []
    
    # Execute Declare War
    _execute_declare_war(engine, "AGRIA", "VULCANIA")
    
    # Verify Initialization
    assert "VULCANIA" in aggressor.active_wars
    assert "AGRIA" in target.active_wars
    
    stats_agg = aggressor.active_wars["VULCANIA"]
    assert stats_agg.start_turn == 5
    assert stats_agg.original_provinces == 3
    assert stats_agg.lost_provinces == 0
    
    stats_tgt = target.active_wars["AGRIA"]
    assert stats_tgt.start_turn == 5
    assert stats_tgt.original_provinces == 2

def test_war_stats_update_on_conquest():
    """Verify WarStats update when provinces are conquered."""
    world = MagicMock(spec=WorldState)
    world.turn = 10
    world.global_events = []
    
    # Setup Nations with Active War
    aggressor = MagicMock(spec=NationState)
    aggressor.id = "AGRIA"
    aggressor.province_ids = [1, 2]
    aggressor.active_wars = {
        "VULCANIA": WarStats(start_turn=5, original_provinces=2)
    }
    aggressor.total_soldiers = 100
    aggressor.total_aircraft = 0
    aggressor.total_navy = 0
    
    target = MagicMock(spec=NationState)
    target.id = "VULCANIA"
    target.province_ids = [10]
    target.active_wars = {
        "AGRIA": WarStats(start_turn=5, original_provinces=1)
    }
    target.total_soldiers = 50
    target.total_aircraft = 0
    target.total_navy = 0
    
    # Setup Province
    province = MagicMock(spec=ProvinceState)
    province.id = 10
    province.owner_id = "VULCANIA"
    province.soldiers = 10
    province.aircraft = 0
    province.neighbors = []
    province.terrain = TerrainType.LAND
    
    world.nations = {"AGRIA": aggressor, "VULCANIA": target}
    world.relationship_matrix = {
        "VULCANIA": {"AGRIA": RelationshipState.WAR},
        "AGRIA": {"VULCANIA": RelationshipState.WAR}
    }
    
    # Execute Conquest
    _conquer_province(world, "AGRIA", province)
    
    # Verify Updates
    # Aggressor (Winner) should have +1 conquered
    assert aggressor.active_wars["VULCANIA"].conquered_provinces == 1
    
    # Target (Loser) should have +1 lost
    assert target.active_wars["AGRIA"].lost_provinces == 1
    
    # Verify province transfer logic (standard)
    assert province.owner_id == "AGRIA"
