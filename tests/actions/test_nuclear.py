"""
Tests for NUCLEAR_OPTION action.

Validates nuclear strike including:
- Validation (has nukes, valid target)
- Devastating effects on province
- Global diplomatic fallout
"""

import pytest
from geomas.world import generate_world
from geomas.actions.engine import ActionEngine
from geomas.actions.defense import (
    DefenseActionType,
    DefensePayload,
    DefenseActionItem,
)
from geomas.actions.common import DecisionSource
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, PublicIntent,
    DefenseIntent, DefenseIntentType,
    EconomicIntent, EconomicIntentType, EconomicPayload,
    ForeignIntent, ForeignIntentType, ForeignPayload,
)


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
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                parameters={"target_province_id": target_province}
            )]
        )
        
        envelope = _create_envelope(nation_id, payload)
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
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                parameters={"target_province_id": own_province}
            )]
        )
        
        envelope = _create_envelope(nation_id, payload)
        logs = engine.execute_envelope(envelope)
        
        assert any("Cannot nuke own territory" in log for log in logs)


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
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                parameters={"target_province_id": target_province_id}
            )]
        )
        
        envelope = _create_envelope(nation_id, payload)
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
            source=DecisionSource.MINISTRY_ADVICE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.NUCLEAR_OPTION,
                parameters={"target_province_id": target_province}
            )]
        )
        
        envelope = _create_envelope(attacker_id, payload)
        engine.execute_envelope(envelope)
        
        # Trust with victim → 0
        assert world.trust_matrix[attacker_id][victim_id] == 0
        assert world.trust_matrix[victim_id][attacker_id] == 0
        
        # Other nations' trust toward attacker decreased by 80 (90 - 80 = 10)
        assert world.trust_matrix[observer_1][attacker_id] == pytest.approx(10, abs=1)
        assert world.trust_matrix[observer_2][attacker_id] == pytest.approx(10, abs=1)


def _create_envelope(nation_id: str, defense_payload: DefensePayload) -> CountryEnvelope:
    """Helper to create a minimal CountryEnvelope for testing."""
    return CountryEnvelope(
        turn=1,
        sender_id=nation_id,
        global_strategy=GlobalStrategy.ARMED_ISOLATIONISM,
        public_statement="Test",
        public_intent=PublicIntent.NEUTRAL,
        defense_payload=defense_payload,
        defense_intent=DefenseIntent(type=DefenseIntentType.IDLE, reasoning="Test"),
        economic_payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE),
        economic_intent=EconomicIntent(type=EconomicIntentType.IDLE, reasoning="Test"),
        foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
        foreign_intent=ForeignIntent(type=ForeignIntentType.IDLE, reasoning="Test"),
    )
