
"""
Tests for Defense Action Validation.

Specifically focuses on strict `target_nation_id` enforcement.
"""

import pytest
from conftest import create_test_envelope
from geomas.world import generate_world
from geomas.actions.engine import ActionEngine
from geomas.actions.defense import (
    DefenseActionType,
    DefensePayload,
    DefenseActionItem,
    UnitType
)
from geomas.schemas.world import TerrainType
from geomas.actions.common import Decision

class TestDefenseStrictValidation:

    def test_create_unit_wrong_nation_id(self):
        """CREATE_UNIT should auto-correct target_nation_id to self (with warning)."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        n1 = list(world.nations.keys())[0]
        n2 = list(world.nations.keys())[1]
        
        p1 = world.nations[n1].province_ids[0]
        
        world.nations[n1].total_budget = 1000
        world.nations[n1].total_materials = 1000
        world.nations[n1].total_workers = 100
        
        # Try to create unit but specifying WRONG target_nation_id
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                unit_type=UnitType.SOLDIER, 
                quantity=1, 
                target_province_id=p1,
                target_nation_id=n2 # WRONG
            )]
        )
        
        initial_soldiers = world.provinces[p1].soldiers
        
        envelope = create_test_envelope(n1, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # 1. Check for correction log
        assert any("CREATE_UNIT: target_nation_id corrected" in log for log in logs)
        
        # 2. Check that unit WAS created (success)
        assert any("Created 1x SOLDIER" in log for log in logs)
        assert world.provinces[p1].soldiers == initial_soldiers + 1

    def test_move_troops_wrong_nation_id(self):
        """MOVE_TROOPS should ignore target_nation_id mismatch (relaxed)."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        n1 = list(world.nations.keys())[0]
        n2 = list(world.nations.keys())[1]
        
        p1 = world.nations[n1].province_ids[0]
        p2_dest = world.nations[n1].province_ids[1] # Destination is also self-owned
        
        # Give soldiers and energy
        world.provinces[p1].soldiers = 10
        world.nations[n1].total_energy = 1000
        
        prov_obj = world.provinces[p1]
        p2_dest = p1 # Default to self
        for neighbor_id in prov_obj.neighbors:
            neigh = world.provinces.get(neighbor_id)
            if neigh and neigh.terrain != TerrainType.OCEAN:
                p2_dest = neighbor_id
                break
        
        # Move P1 -> P2, but say target_nation_id is N2 (Wrong)
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                unit_type=UnitType.SOLDIER, 
                quantity=1, 
                source_province_id=p1,
                target_province_id=p2_dest,
                target_nation_id=n2 # WRONG
            )]
        )
        
        envelope = create_test_envelope(n1, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Assert NO error message about mismatch
        assert not any("does not match destination owner" in log for log in logs)
        
        # Assert successful move
        if p1 != p2_dest:
            assert any("Moved 1x SOLDIER" in log for log in logs)
        else:
            # If same province, it might be a no-op but shouldn't fail validation
            pass

    def test_nuclear_wrong_target_id(self):
        """NUCLEAR_OPTION target_nation_id must match province owner."""
        world = generate_world(seed=42, n_cells=50, n_nations=3)
        engine = ActionEngine(world)
        
        n1 = list(world.nations.keys())[0]
        n2 = list(world.nations.keys())[1] # Victim
        n3 = list(world.nations.keys())[2] # Bystander
        
        p_victim = world.nations[n2].province_ids[0]
        world.nations[n1].nukes = 10
        
        # Attack N2's province but say target is N3
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                target_province_id=p_victim,
                target_nation_id=n3 # WRONG
            )]
        )
        
        envelope = create_test_envelope(n1, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        assert any("does not match province owner" in log for log in logs)

    def test_nuclear_target_self_fail(self):
        """Cannot nuke self even if target_nation_id matches self."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        n1 = list(world.nations.keys())[0]
        p1 = world.nations[n1].province_ids[0]
        world.nations[n1].nukes = 10
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                target_province_id=p1,
                target_nation_id=n1 # Targeting self
            )]
        )
        
        envelope = create_test_envelope(n1, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Check logs for strict match or substring
        print(f"DEBUG: Payload moves: {payload.moves}")
        print(f"DEBUG: Logs: {logs}")
        assert any("Cannot target SELF" in log for log in logs)
