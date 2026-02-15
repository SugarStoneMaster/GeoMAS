
import pytest
from unittest.mock import MagicMock
from geomas.actions.defense.handler import _execute_move_troops
from geomas.actions.defense.schemas import DefenseActionItem, DefenseActionType, UnitType
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType
from geomas.actions.engine import ActionEngine

def test_combat_log_shows_old_owner():
    """Verify that combat logs include the nation that lost the province."""
    # Setup World
    world = MagicMock(spec=WorldState)
    attacker_id = "AGRIA"
    defender_id = "VULCANIA"
    province_id = 91
    
    attacker = MagicMock(spec=NationState)
    attacker.total_energy = 1000
    attacker.total_soldiers = 100
    attacker.total_aircraft = 0
    attacker.total_navy = 0
    attacker.province_ids = [80]
    attacker.nukes = 0
    
    defender = MagicMock(spec=NationState)
    defender.total_soldiers = 50
    defender.total_aircraft = 0
    defender.total_navy = 0
    defender.province_ids = [91]
    defender.nukes = 0
    
    # Province being attacked
    target_province = MagicMock(spec=ProvinceState)
    target_province.id = province_id
    target_province.owner_id = defender_id
    target_province.soldiers = 0  # Undefended for easy conquest
    target_province.aircraft = 0
    target_province.navy = 0
    target_province.terrain = TerrainType.LAND
    target_province.neighbors = [80]
    
    # Source province
    source_province = MagicMock(spec=ProvinceState)
    source_province.id = 80
    source_province.owner_id = attacker_id
    source_province.soldiers = 50
    source_province.terrain = TerrainType.LAND
    
    world.nations = {attacker_id: attacker, defender_id: defender}
    world.provinces = {province_id: target_province, 80: source_province}
    world.turn = 1
    
    # Mock ActionEngine
    engine = MagicMock(spec=ActionEngine)
    engine.world = world
    engine.logs = []
    engine.spatial = MagicMock()
    engine.spatial.get_shortest_path.return_value = [80, province_id]
    
    # Move/Attack Action
    move = DefenseActionItem(
        action_type=DefenseActionType.MOVE_TROOPS,
        unit_type=UnitType.SOLDIER,
        quantity=50,
        source_province_id=80,
        target_province_id=province_id,
        priority=1
    )
    
    # Execute
    _execute_move_troops(engine, attacker_id, move)
    
    # Verify Logs
    found = False
    for log in engine.logs:
        if f"conquered by {attacker_id} (lost by {defender_id})" in log:
            found = True
            break
    
    assert found, f"Expected log with 'lost by {defender_id}' not found in: {engine.logs}"

def test_neutral_combat_log():
    """Verify that neutral province capture is logged correctly."""
    # Setup World
    world = MagicMock(spec=WorldState)
    attacker_id = "AGRIA"
    province_id = 100
    
    attacker = MagicMock(spec=NationState)
    attacker.total_energy = 1000
    attacker.total_soldiers = 100
    attacker.total_aircraft = 0
    attacker.total_navy = 0
    attacker.province_ids = [80]
    attacker.nukes = 0
    
    # Neutral Province
    target_province = MagicMock(spec=ProvinceState)
    target_province.id = province_id
    target_province.owner_id = None # NEUTRAL
    target_province.soldiers = 0
    target_province.aircraft = 0
    target_province.navy = 0
    target_province.terrain = TerrainType.LAND
    target_province.neighbors = [80]
    
    # Source province
    source_province = MagicMock(spec=ProvinceState)
    source_province.id = 80
    source_province.owner_id = attacker_id
    source_province.soldiers = 50
    source_province.terrain = TerrainType.LAND
    
    world.nations = {attacker_id: attacker}
    world.provinces = {province_id: target_province, 80: source_province}
    world.turn = 1
    
    # Mock ActionEngine
    engine = MagicMock(spec=ActionEngine)
    engine.world = world
    engine.logs = []
    engine.spatial = MagicMock()
    engine.spatial.get_shortest_path.return_value = [80, province_id]
    
    # Move Action
    move = DefenseActionItem(
        action_type=DefenseActionType.MOVE_TROOPS,
        unit_type=UnitType.SOLDIER,
        quantity=50,
        source_province_id=80,
        target_province_id=province_id,
        priority=1
    )
    
    # Execute
    _execute_move_troops(engine, attacker_id, move)
    
    # Verify Logs
    found = False
    for log in engine.logs:
        if f"conquered by {attacker_id} (from NEUTRAL)" in log:
            found = True
            break
    
    assert found, f"Expected log with '(from NEUTRAL)' not found in: {engine.logs}"
