"""
Tests for NUCLEAR_OPTION action.

Validates nuclear strike including:
- Validation (has nukes, valid target)
- Devastating effects on province
- Global diplomatic fallout
"""

import pytest
from conftest import create_test_envelope
from geomas.world import generate_world
from geomas.actions.engine import ActionEngine
from geomas.actions.defense import (
    DefenseActionType,
    DefensePayload,
    DefenseActionItem,
)
from geomas.actions.common import Decision


class TestNuclearValidation:
    """Tests for nuclear strike validation."""
    
    def test_no_nukes_fails(self):
        """Cannot nuke without nukes."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        enemy_id = list(world.nations.keys())[1]
        nation = world.nations[nation_id]
        
        # Ensure no nukes
        nation.nukes = 0
        
        target_province = world.nations[enemy_id].province_ids[0]
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                target_province_id=target_province,
                target_nation_id=enemy_id
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        assert any("Insufficient nukes" in log for log in logs)
    
    def test_cannot_nuke_own_territory(self):
        """Cannot nuke own province."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        nation.nukes = 10
        
        # Target own province
        own_province = nation.province_ids[0]
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                target_province_id=own_province,
                target_nation_id=nation_id # Targeting self should fail
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Check logs for strict match or substring
        # Since we check target_nation_id first, we expect "Cannot target SELF"
        assert any("Cannot target SELF" in log for log in logs)


class TestNuclearEffects:
    """Tests for nuclear strike effects."""
    
    def test_province_devastated(self):
        """Nuclear strike devastates province."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        nation_id = list(world.nations.keys())[0]
        enemy_id = list(world.nations.keys())[1]
        nation = world.nations[nation_id]
        nation.nukes = 10
        
        target_province_id = world.nations[enemy_id].province_ids[0]
        target_province = world.provinces[target_province_id]
        
        # Setup defenders
        target_province.soldiers = 50
        target_province.aircraft = 10
        target_province.population = 1000
        
        initial_pop = target_province.population
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                target_province_id=target_province_id,
                target_nation_id=enemy_id
            )]
        )
        
        envelope = create_test_envelope(nation_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Verify devastation
        assert target_province.soldiers == 0
        assert target_province.aircraft == 0
        assert target_province.population == int(initial_pop * 0.1)
        assert "☢️" in str(logs)  # Nuke emoji in log
    
    def test_global_trust_decrease(self):
        """All nations lose trust with nuclear aggressor."""
        world = generate_world(seed=42, n_cells=50, n_nations=4)
        engine = ActionEngine(world)
        
        nation_ids = list(world.nations.keys())
        attacker_id = nation_ids[0]
        victim_id = nation_ids[1]
        observer_1 = nation_ids[2]
        observer_2 = nation_ids[3]
        
        world.nations[attacker_id].nukes = 10
        target_province = world.nations[victim_id].province_ids[0]
        
        # Set initial trust (0-100 scale)
        for n_id in nation_ids:
            world.trust_matrix.setdefault(n_id, {})
            for other_id in nation_ids:
                if n_id != other_id:
                    world.trust_matrix[n_id][other_id] = 90
        
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                target_province_id=target_province,
                target_nation_id=victim_id
            )]
        )
        
        envelope = create_test_envelope(attacker_id, defense_payload=payload)
        engine.execute_envelope(envelope)
        
        # Trust with victim → 0
        assert world.trust_matrix[attacker_id][victim_id] == 0
        assert world.trust_matrix[victim_id][attacker_id] == 0
        
        # Other nations' trust toward attacker decreased by 80 (90 - 80 = 10)
        assert world.trust_matrix[observer_1][attacker_id] == pytest.approx(10, abs=1)
        assert world.trust_matrix[observer_2][attacker_id] == pytest.approx(10, abs=1)

