"""
Tests for Foreign Affairs / Diplomacy System.

Validates diplomatic actions and relationship state management.
"""

import pytest
from geomas.world import generate_world
from geomas.actions.engine import ActionEngine
from geomas.actions.foreign import (
    ForeignActionType,
    ForeignPayload,
    DiplomaticMessageType,
    MESSAGE_TRUST_IMPACT,
    execute_foreign,
)
from geomas.actions.common import DecisionSource
from geomas.schemas.world import RelationshipState


class TestRelationshipStates:
    """Tests for relationship state management."""
    
    def test_relationship_enum_values(self):
        """RelationshipState has correct values."""
        assert RelationshipState.PEACE.value == "PEACE"
        assert RelationshipState.WAR.value == "WAR"
        assert RelationshipState.ALLIANCE.value == "ALLIANCE"
    
    def test_default_relationship_is_peace(self):
        """All nations start at PEACE."""
        world = generate_world(seed=42, n_cells=50, n_nations=3)
        
        nation_ids = list(world.nations.keys())
        
        for n_a in nation_ids:
            for n_b in nation_ids:
                if n_a != n_b:
                    rel = world.relationship_matrix.get(n_a, {}).get(n_b)
                    assert rel == "PEACE", f"{n_a} vs {n_b} is {rel}, expected PEACE"


class TestDiplomaticMessages:
    """Tests for diplomatic message actions."""
    
    def test_praise_increases_trust(self):
        """PRAISE message increases trust."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        sender_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        initial_trust = world.trust_matrix[sender_id][target_id]
        
        payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE,
            target_nation_id=target_id,
            parameters={"message_type": "PRAISE"}
        )
        
        execute_foreign(engine, sender_id, payload)
        
        new_trust = world.trust_matrix[sender_id][target_id]
        assert new_trust > initial_trust
    
    def test_threat_decreases_trust(self):
        """THREAT message decreases trust significantly."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        sender_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        initial_trust = world.trust_matrix[sender_id][target_id]
        
        payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE,
            target_nation_id=target_id,
            parameters={"message_type": "THREAT"}
        )
        
        execute_foreign(engine, sender_id, payload)
        
        new_trust = world.trust_matrix[sender_id][target_id]
        assert new_trust < initial_trust
        assert new_trust == pytest.approx(initial_trust - 0.3, abs=0.01)


class TestDeclarationOfWar:
    """Tests for war declaration."""
    
    def test_declare_war_changes_relationship(self):
        """Declaration of war sets relationship to WAR."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        aggressor_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.FORMAL_DECLARATION_OF_WAR,
            target_nation_id=target_id,
        )
        
        execute_foreign(engine, aggressor_id, payload)
        
        assert world.relationship_matrix[aggressor_id][target_id] == "WAR"
        assert world.relationship_matrix[target_id][aggressor_id] == "WAR"
        assert world.trust_matrix[aggressor_id][target_id] == 0.0


class TestProposeAlliance:
    """Tests for alliance proposals."""
    
    def test_alliance_requires_high_trust(self):
        """Alliance rejected if trust too low."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        proposer_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        # Set trust too low
        world.trust_matrix[proposer_id][target_id] = 0.4
        
        payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.PROPOSE_ALLIANCE,
            target_nation_id=target_id,
        )
        
        execute_foreign(engine, proposer_id, payload)
        
        # Should still be PEACE (rejected)
        assert world.relationship_matrix[proposer_id][target_id] == "PEACE"
    
    def test_alliance_accepted_with_high_trust(self):
        """Alliance accepted if trust high enough."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        proposer_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        # Set trust high
        world.trust_matrix[proposer_id][target_id] = 0.8
        
        payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.PROPOSE_ALLIANCE,
            target_nation_id=target_id,
        )
        
        execute_foreign(engine, proposer_id, payload)
        
        assert world.relationship_matrix[proposer_id][target_id] == "ALLIANCE"
        assert world.relationship_matrix[target_id][proposer_id] == "ALLIANCE"
