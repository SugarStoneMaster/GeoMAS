import pytest
from unittest.mock import MagicMock
from geomas.actions.defense.handler import _execute_move_troops
from geomas.actions.defense.combat import get_total_defenders
from geomas.actions.defense.schemas import DefenseActionItem, DefenseActionType, UnitType
from geomas.schemas.world import WorldState, NationState, ProvinceState, RelationshipState, TerrainType
from geomas.actions.engine import ActionEngine

def test_allied_guest_troops_defense():
    """Verify that guest troops participate in defense and get destroyed on defeat."""
    world = MagicMock(spec=WorldState)
    attacker_id = "AGRIA"
    defender_id = "VULCANIA"
    guest_id = "CIMMERIA"
    province_id = 91
    
    attacker = MagicMock(spec=NationState)
    attacker.total_energy = 1000
    attacker.total_soldiers = 500  # Overwhelming force
    attacker.total_aircraft = 0
    attacker.total_navy = 0
    attacker.province_ids = [80]
    attacker.nukes = 0
    attacker.active_wars = {}
    
    defender = MagicMock(spec=NationState)
    defender.total_soldiers = 10
    defender.total_aircraft = 0
    defender.total_navy = 0
    defender.province_ids = [91]
    defender.nukes = 0
    defender.active_wars = {}
    
    guest = MagicMock(spec=NationState)
    guest.total_soldiers = 20
    guest.total_aircraft = 0
    guest.total_navy = 0
    guest.province_ids = [92]
    guest.nukes = 0
    guest.active_wars = {}
    
    # Province being attacked
    target_province = MagicMock(spec=ProvinceState)
    target_province.id = province_id
    target_province.owner_id = defender_id
    target_province.soldiers = 10
    target_province.aircraft = 0
    target_province.navy = 0
    target_province.terrain = TerrainType.LAND
    target_province.neighbors = [80]
    target_province.guest_troops = {
        guest_id: {"soldiers": 20, "aircraft": 0}
    }
    
    # Source province
    source_province = MagicMock(spec=ProvinceState)
    source_province.id = 80
    source_province.owner_id = attacker_id
    source_province.soldiers = 500
    source_province.terrain = TerrainType.LAND
    source_province.guest_troops = {}
    
    world.nations = {attacker_id: attacker, defender_id: defender, guest_id: guest}
    world.provinces = {province_id: target_province, 80: source_province}
    world.turn = 1
    
    # Establish alliances
    world.relationship_matrix = {
        attacker_id: {
            defender_id: RelationshipState.WAR,
            guest_id: RelationshipState.PEACE
        },
        defender_id: {
            attacker_id: RelationshipState.WAR,
            guest_id: RelationshipState.MUTUAL_DEFENSE
        },
        guest_id: {
            attacker_id: RelationshipState.PEACE,
            defender_id: RelationshipState.MUTUAL_DEFENSE
        }
    }
    world.trust_matrix = {}
    
    # Mock ActionEngine
    engine = MagicMock(spec=ActionEngine)
    engine.world = world
    engine.logs = []
    
    # Stub trust adjust securely
    def mock_adjust_trust(n_from, n_to, amount):
        pass
    engine.adjust_trust = mock_adjust_trust
    
    engine.spatial = MagicMock()
    engine.spatial.get_shortest_path.return_value = [80, province_id]
    engine.spatial.get_permitted_path.return_value = [80, province_id]
    
    # Validate Total Defenders includes guest
    t_sol, t_air = get_total_defenders(target_province)
    assert t_sol == 30  # 10 owner + 20 guest
    
    # Attack with Overwhelming Force
    move = DefenseActionItem(
        action_type=DefenseActionType.MOVE_TROOPS,
        unit_type=UnitType.SOLDIER,
        quantity=500,
        source_province_id=80,
        target_province_id=province_id,
        priority=1
    )
    
    # Execute Attack
    _execute_move_troops(engine, attacker_id, move)
    
    # 1. Did the province change owner?
    assert target_province.owner_id == attacker_id
    
    # 2. Were guest troops destroyed conceptually?
    assert len(target_province.guest_troops) == 0
    
    # 3. Were the guest nation's national totals decremented?
    assert guest.total_soldiers == 0  # started with 20, lost 20
    assert defender.total_soldiers == 0  # started with 10, lost 10
    
    # 4. Did attacking guest troops trigger a war automatically with the guest nation?
    assert world.relationship_matrix[attacker_id][guest_id] == RelationshipState.WAR
    assert world.relationship_matrix[guest_id][attacker_id] == RelationshipState.WAR
    
    # 5. Did proper war stats initialize for the guest nation?
    assert guest_id in attacker.active_wars
    assert attacker_id in guest.active_wars
