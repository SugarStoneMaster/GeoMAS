"""
Tests for CREATE_UNIT Defense Action.

Validates complete unit creation flow including:
- Resource validation and deduction
- Terrain constraints
- Province ownership
- Unit placement in provinces
"""

import pytest
from conftest import create_test_envelope
from geomas.world import generate_world
from geomas.actions.engine import ActionEngine
from geomas.actions.defense import (
    DefenseActionType,
    DefensePayload,
    DefenseActionItem,
    UnitType,
    UNIT_COSTS,
)
from geomas.actions.common import DecisionSource
from geomas.schemas.world import TerrainType


class TestCreateUnitValidation:
    """Tests for CREATE_UNIT input validation."""
    
    def test_invalid_unit_type(self):
        """Invalid unit type should fail gracefully."""
        world = generate_world(seed=42, n_cells=50, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        
        payload = DefensePayload(
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "INVALID_TYPE", "quantity": 1}
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        assert any("Invalid unit type" in log for log in logs)
    
    def test_province_not_owned(self):
        """Cannot create units in provinces not owned by the nation."""
        world = generate_world(seed=42, n_cells=100, n_nations=2)
        engine = ActionEngine(world)
        nation_ids = list(world.nations.keys())
        nation_a = nation_ids[0]
        nation_b = nation_ids[1]
        
        # Get a province owned by nation B
        enemy_province = world.nations[nation_b].province_ids[0]
        
        # Set up resources
        world.nations[nation_a].total_budget = 100.0
        world.nations[nation_a].total_materials = 50.0
        world.nations[nation_a].total_workers = 10
        
        payload = DefensePayload(
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "SOLDIER", "quantity": 1, "province_id": int(enemy_province)}
            )]
        )
        
        envelope = create_test_envelope(nation_a, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        assert any("not owned" in log for log in logs)
    
    def test_terrain_constraint_soldier_on_ocean(self):
        """Soldiers cannot be placed on ocean terrain (territorial waters)."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Find a territorial water (ocean that we "own" for navy)
        if not nation.territorial_water_ids:
            pytest.skip("No territorial waters found")
        
        ocean_prov = nation.territorial_water_ids[0]
        initial_soldiers = nation.total_soldiers
        
        nation.total_budget = 100.0
        nation.total_materials = 50.0
        nation.total_workers = 10
        
        # Try to place SOLDIER in ocean (should fail - not owned or terrain)
        payload = DefensePayload(
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "SOLDIER", "quantity": 1, "province_id": int(ocean_prov)}
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Either "not owned" or "Cannot place" error - soldier should NOT be created
        assert nation.total_soldiers == initial_soldiers  # No soldiers added


class TestCreateUnitExecution:
    """Tests for successful CREATE_UNIT execution."""
    
    def test_create_soldier_success(self):
        """Successfully create soldiers in an owned province."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Get a land province
        target_province = None
        for pid in nation.province_ids:
            prov = world.provinces[pid]
            if prov.terrain in [TerrainType.LAND, TerrainType.COASTAL, TerrainType.MOUNTAIN]:
                target_province = pid
                break
        
        if target_province is None:
            pytest.skip("No land province found")
        
        # Setup resources
        nation.total_budget = 100.0
        nation.total_materials = 50.0
        nation.total_energy = 20.0
        nation.total_workers = 20
        
        initial_soldiers = world.provinces[target_province].soldiers
        initial_total_soldiers = nation.total_soldiers
        
        payload = DefensePayload(
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "SOLDIER", "quantity": 5, "province_id": int(target_province)}
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Verify units created
        assert world.provinces[target_province].soldiers == initial_soldiers + 5
        assert nation.total_soldiers == initial_total_soldiers + 5
        
        # Verify resources deducted (SOLDIER: 5 budget, 2 materials per unit)
        assert nation.total_budget == 100.0 - (5 * 5)  # 75
        assert nation.total_materials == 50.0 - (5 * 2)  # 40
        assert nation.total_workers == 20 - 5  # Workers become soldiers
        
        assert any("Created 5x SOLDIER" in log for log in logs)
    
    def test_create_aircraft_success(self):
        """Successfully create aircraft in an owned province."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Get a land province
        target_province = nation.capital_province_id
        
        # Setup resources (AIRCRAFT: 80 budget, 40 materials, 10 energy, 5 pop)
        nation.total_budget = 200.0
        nation.total_materials = 100.0
        nation.total_energy = 30.0
        nation.total_workers = 20
        
        initial_aircraft = world.provinces[target_province].aircraft
        
        payload = DefensePayload(
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "AIRCRAFT", "quantity": 2, "province_id": int(target_province)}
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Verify units created
        assert world.provinces[target_province].aircraft == initial_aircraft + 2
        assert nation.total_aircraft >= 2
        
        # Verify resources deducted
        assert nation.total_budget == 200.0 - (2 * 80)  # 40
        assert nation.total_materials == 100.0 - (2 * 40)  # 20
        assert nation.total_energy == 30.0 - (2 * 10)  # 10
        
        assert any("Created 2x AIRCRAFT" in log for log in logs)
    
    def test_create_navy_in_territorial_waters(self):
        """Successfully create navy in territorial waters."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Get territorial water
        if not nation.territorial_water_ids:
            pytest.skip("No territorial waters found")
        
        target_water = nation.territorial_water_ids[0]
        
        # Setup resources (NAVY: 50 budget, 30 materials, 5 energy, 10 pop)
        nation.total_budget = 200.0
        nation.total_materials = 100.0
        nation.total_energy = 20.0
        nation.total_workers = 30
        
        initial_navy = world.provinces[target_water].navy
        
        payload = DefensePayload(
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "NAVY", "quantity": 2, "province_id": int(target_water)}
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Verify units created
        assert world.provinces[target_water].navy == initial_navy + 2
        assert nation.total_navy >= 2
        
        assert any("Created 2x NAVY" in log for log in logs)
    
    def test_default_to_capital_province(self):
        """If no province specified, default to capital."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        capital = nation.capital_province_id
        nation.total_budget = 100.0
        nation.total_materials = 50.0
        nation.total_workers = 10
        
        initial_soldiers = world.provinces[capital].soldiers
        
        # No province_id specified
        payload = DefensePayload(
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                parameters={"unit_type": "SOLDIER", "quantity": 1}
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Should create in capital
        assert world.provinces[capital].soldiers == initial_soldiers + 1
        assert any("Created 1x SOLDIER" in log for log in logs)


