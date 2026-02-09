
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
from geomas.actions.common import Decision

class TestDefenseStrictValidation:

    def test_create_unit_wrong_nation_id(self):
        """CREATE_UNIT must have target_nation_id == self."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        n1 = list(world.nations.keys())[0]
        n2 = list(world.nations.keys())[1]
        
        p1 = world.nations[n1].province_ids[0]
        
        world.nations[n1].total_budget = 1000
        world.nations[n1].total_materials = 1000
        world.nations[n1].total_workers = 100
        
        # Try to create unit but specifying WRONG target_nation_id
        # Even if province is valid (owned by self), specificing n2 should fail
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.CREATE_UNIT,
                unit_type="SOLDIER", 
                quantity=1, 
                target_province_id=p1,
                target_nation_id=n2 # WRONG
            )]
        )
        
        envelope = create_test_envelope(n1, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        assert any(f"target_nation_id {n2} must be {n1}" in log for log in logs)

    def test_move_troops_wrong_nation_id(self):
        """MOVE_TROOPS target_nation_id must match destination owner completely."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        n1 = list(world.nations.keys())[0]
        n2 = list(world.nations.keys())[1]
        
        p1 = world.nations[n1].province_ids[0]
        p2_enemy = world.nations[n2].province_ids[0]
        
        # Give soldiers and energy
        world.provinces[p1].soldiers = 10
        world.nations[n1].total_energy = 1000
        
        # Try to move to enemy province but claim target_nation_id is SELF (lie)
        # Should fail validation
        # (Assuming adjacent or teleport for validation test - logic checks ID first if path valid)
        # We need a valid path first. Let's pick adjacent if possible, or just mock path finding?
        # The logic checks ownership mismatch BEFORE path finding? No, checking handler...
        # It checks ownership mismatch inside the function.
        # But wait, create_unit checks it early. move_troops check it after basic param validation.
        
        # Let's simplify: try to move to SELF province but say target_nation_id is ENEMY
        p1_dest = world.nations[n1].province_ids[1] # Another self province
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                unit_type="SOLDIER", 
                quantity=1, 
                source_province_id=p1,
                target_province_id=p1_dest,
                target_nation_id=n2 # WRONG: destination is owned by n1
            )]
        )
        
        envelope = create_test_envelope(n1, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Fix assertion: check if any log contains the error message
        assert any("does not match destination owner" in log for log in logs)

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
