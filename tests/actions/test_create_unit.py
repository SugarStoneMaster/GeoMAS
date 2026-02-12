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
from geomas.actions.common import Decision
from geomas.schemas.world import TerrainType


class TestCreateUnitValidation:
    """Tests for CREATE_UNIT input validation."""
    
    def test_invalid_unit_type(self):
        """When unit_type is None, validation should fail (no default)."""
        world = generate_world(seed=42, n_cells=50, n_nations=1)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        target_province = nation.province_ids[0]
        
        with pytest.raises(ValueError):
            DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                unit_type=None,  # Should fail validation
                quantity=1,
                target_province_id=int(target_province),
                target_nation_id=nation_id
            )
    
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
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                unit_type="SOLDIER", 
                quantity=1, 
                target_province_id=int(enemy_province),
                target_nation_id=nation_a
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
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                unit_type="SOLDIER", 
                quantity=1, 
                target_province_id=int(ocean_prov),
                target_nation_id=nation_id
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
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                unit_type="SOLDIER", 
                quantity=5, 
                target_province_id=int(target_province),
                target_nation_id=nation_id
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
        target_province = nation.province_ids[0]
        
        # Setup resources (AIRCRAFT: 80 budget, 40 materials, 10 energy, 5 pop)
        nation.total_budget = 200.0
        nation.total_materials = 100.0
        nation.total_energy = 30.0
        nation.total_workers = 20
        
        initial_aircraft = world.provinces[target_province].aircraft
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                unit_type="AIRCRAFT", 
                quantity=2, 
                target_province_id=int(target_province),
                target_nation_id=nation_id
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
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                unit_type="NAVY", 
                quantity=2, 
                target_province_id=int(target_water),
                target_nation_id=nation_id
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Verify units created
        assert world.provinces[target_water].navy == initial_navy + 2
        assert nation.total_navy >= 2
        
        assert any("Created 2x NAVY" in log for log in logs)
    
    def test_no_province_fails(self):
        """If no province specified, creation should fail validation."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Should raise ValidationError due to missing target_province_id
        with pytest.raises(ValueError):
            DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                unit_type="SOLDIER", 
                quantity=1,
                target_nation_id=nation_id
                # Missing target_province_id
            )

