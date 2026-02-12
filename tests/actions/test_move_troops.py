"""
Tests for MOVE_TROOPS Defense Action.

Validates troop movement including:
- Path validation for different unit types
- Energy cost calculation
- Range limits
- Unit transfer between provinces
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
    MOVEMENT_ENERGY_COST,
    MOVEMENT_RANGE,
)
from geomas.actions.common import Decision
from geomas.schemas.world import TerrainType


class TestMoveTroopsValidation:
    """Tests for MOVE_TROOPS input validation."""
    
    def test_missing_provinces(self):
        """Must specify validation fails if source/target missing."""
        world = generate_world(seed=42, n_cells=50, n_nations=1)
        nation_id = list(world.nations.keys())[0]
        
        # Should raise ValidationError due to missing source_province_id/target_province_id
        with pytest.raises(ValueError):
            DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                unit_type="SOLDIER", 
                quantity=1,
                target_nation_id=nation_id
            )
    
    def test_not_enough_units(self):
        """Moving more units than available should clamp to available quantity."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Get two adjacent non-ocean provinces
        province_a = None
        province_b = None
        for pid in nation.province_ids:
            prov = world.provinces[pid]
            if prov.terrain == TerrainType.OCEAN:
                continue
            for neighbor_id in prov.neighbors:
                n_prov = world.provinces.get(neighbor_id)
                if n_prov and n_prov.owner_id == nation_id and n_prov.terrain != TerrainType.OCEAN:
                    province_a = pid
                    province_b = neighbor_id
                    break
            if province_a:
                break
        
        if province_a is None or province_b is None:
            pytest.skip("No adjacent owned non-ocean provinces found")
        
        # Set soldiers = 5 in province A
        world.provinces[province_a].soldiers = 5
        world.provinces[province_b].soldiers = 0
        nation.total_energy = 100.0
        
        # Try to move 10 (only 5 available)
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                unit_type="SOLDIER",
                quantity=10,
                source_province_id=int(province_a),
                target_province_id=int(province_b),
                target_nation_id=nation_id
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Should clamp to 5 and succeed
        assert any("Clamped" in log for log in logs)
        assert any("Moved 5x SOLDIER" in log for log in logs)
        assert world.provinces[province_a].soldiers == 0
        assert world.provinces[province_b].soldiers == 5
    
    def test_insufficient_energy(self):
        """Movement requires energy."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Get two adjacent provinces
        province_a = nation.province_ids[0]
        province_b = None
        for neighbor_id in world.provinces[province_a].neighbors:
            prov = world.provinces.get(neighbor_id)
            if prov and prov.owner_id == nation_id:
                province_b = neighbor_id
                break
        
        if province_b is None:
            pytest.skip("No adjacent owned province found")
        
        # Set soldiers and energy
        world.provinces[province_a].soldiers = 10
        nation.total_energy = 0.0  # No energy!
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                unit_type="SOLDIER",
                quantity=5,
                source_province_id=int(province_a),
                target_province_id=int(province_b),
                target_nation_id=nation_id
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        assert any("Insufficient energy" in log for log in logs)


class TestMoveTroopsExecution:
    """Tests for successful MOVE_TROOPS execution."""
    
    def test_move_soldiers_adjacent(self):
        """Successfully move soldiers to adjacent owned province."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Find two adjacent owned land provinces
        province_a = None
        province_b = None
        
        for pid in nation.province_ids:
            prov = world.provinces[pid]
            if prov.terrain != TerrainType.OCEAN:
                for neighbor_id in prov.neighbors:
                    neighbor = world.provinces.get(neighbor_id)
                    if neighbor and neighbor.owner_id == nation_id and neighbor.terrain != TerrainType.OCEAN:
                        province_a = pid
                        province_b = neighbor_id
                        break
            if province_a:
                break
        
        if province_a is None or province_b is None:
            pytest.skip("Could not find two adjacent owned land provinces")
        
        # Setup
        world.provinces[province_a].soldiers = 10
        world.provinces[province_b].soldiers = 5
        nation.total_energy = 100.0
        
        initial_a = 10
        initial_b = 5
        initial_energy = 100.0
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                unit_type="SOLDIER",
                quantity=3,
                source_province_id=int(province_a),
                target_province_id=int(province_b),
                target_nation_id=nation_id
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Verify units moved
        assert world.provinces[province_a].soldiers == initial_a - 3
        assert world.provinces[province_b].soldiers == initial_b + 3
        
        # Verify energy deducted (distance 1, 3 soldiers * 0.1 energy * 1 hop = 0.3)
        expected_energy_cost = 3 * MOVEMENT_ENERGY_COST[UnitType.SOLDIER] * 1
        assert nation.total_energy == initial_energy - expected_energy_cost
        
        assert any("Moved 3x SOLDIER" in log for log in logs)
    
    def test_move_aircraft_long_range(self):
        """Aircraft can move longer distances."""
        world = generate_world(seed=42, n_cells=100, n_nations=1)
        engine = ActionEngine(world)
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        # Get a starting province and find a destination within aircraft range
        start_province = nation.province_ids[0]
        dest_province = None
        
        for pid in nation.province_ids:
            if pid == start_province:
                continue
            prov = world.provinces[pid]
            if prov.terrain == TerrainType.OCEAN:
                continue
            # Check distance is within aircraft range (6)
            path = engine.spatial.get_shortest_path(start_province, pid)
            if path and len(path) - 1 <= MOVEMENT_RANGE[UnitType.AIRCRAFT]:
                dest_province = pid
                break
        
        if dest_province is None:
            pytest.skip("No reachable destination within aircraft range")
        
        # Setup aircraft
        world.provinces[start_province].aircraft = 5
        nation.total_energy = 500.0
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                unit_type="AIRCRAFT",
                quantity=2,
                source_province_id=int(start_province),
                target_province_id=int(dest_province),
                target_nation_id=nation_id
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Verify aircraft moved
        assert world.provinces[start_province].aircraft == 3
        assert world.provinces[dest_province].aircraft >= 2
        
        assert any("Moved 2x AIRCRAFT" in log for log in logs)


