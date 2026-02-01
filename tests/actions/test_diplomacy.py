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
    MESSAGE_COOLDOWN_TURNS,
    execute_foreign,
    clear_expired_proposals,
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
        """Alliance proposal creates pending, then acceptance forms alliance."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        proposer_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        # Set trust high
        world.trust_matrix[proposer_id][target_id] = 0.8
        
        # Step 1: Propose alliance (creates pending)
        propose_payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.PROPOSE_ALLIANCE,
            target_nation_id=target_id,
        )
        execute_foreign(engine, proposer_id, propose_payload)
        
        # Check pending proposal created
        target_nation = world.nations[target_id]
        assert len(target_nation.pending_proposals) == 1
        assert target_nation.pending_proposals[0]["type"] == "ALLIANCE"
        assert target_nation.pending_proposals[0]["from"] == proposer_id
        
        # Still PEACE until accepted
        assert world.relationship_matrix[proposer_id][target_id] == "PEACE"
        
        # Step 2: Accept the proposal
        accept_payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.ACCEPT_PROPOSAL,
            target_nation_id=proposer_id,
            parameters={"proposal_type": "ALLIANCE"}
        )
        execute_foreign(engine, target_id, accept_payload)
        
        # Now should be ALLIANCE
        assert world.relationship_matrix[proposer_id][target_id] == "ALLIANCE"
        assert world.relationship_matrix[target_id][proposer_id] == "ALLIANCE"


class TestMessageCooldown:
    """Tests for message anti-spam cooldown."""
    
    def test_message_blocked_during_cooldown(self):
        """Cannot send message to same nation within cooldown period."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        world.turn = 1
        
        sender_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        initial_trust = world.trust_matrix[sender_id][target_id]
        
        payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE,
            target_nation_id=target_id,
            parameters={"message_type": "PRAISE"}
        )
        
        # First message works
        execute_foreign(engine, sender_id, payload)
        trust_after_first = world.trust_matrix[sender_id][target_id]
        assert trust_after_first > initial_trust
        
        # Second message same turn - blocked by cooldown
        world.turn = 2
        execute_foreign(engine, sender_id, payload)
        trust_after_second = world.trust_matrix[sender_id][target_id]
        assert trust_after_second == trust_after_first  # No change
        assert any("cooldown" in log.lower() for log in engine.logs)
    
    def test_message_allowed_after_cooldown(self):
        """Can send message after cooldown expires."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        world.turn = 1
        
        sender_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.SEND_DIPLOMATIC_MESSAGE,
            target_nation_id=target_id,
            parameters={"message_type": "PRAISE"}
        )
        
        # First message at turn 1
        execute_foreign(engine, sender_id, payload)
        trust_after_first = world.trust_matrix[sender_id][target_id]
        
        # Message after cooldown (turn 1 + 5 = 6)
        world.turn = 1 + MESSAGE_COOLDOWN_TURNS
        execute_foreign(engine, sender_id, payload)
        trust_after_cooldown = world.trust_matrix[sender_id][target_id]
        assert trust_after_cooldown > trust_after_first


class TestProposalExpiry:
    """Tests for proposal expiration."""
    
    def test_proposal_expires_after_one_turn(self):
        """Proposal created at turn 5 expires by turn 7."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        proposer_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        world.trust_matrix[proposer_id][target_id] = 0.8
        
        # Create proposal at turn 5
        world.turn = 5
        propose_payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.PROPOSE_ALLIANCE,
            target_nation_id=target_id,
        )
        execute_foreign(engine, proposer_id, propose_payload)
        
        # Proposal exists
        target_nation = world.nations[target_id]
        assert len(target_nation.pending_proposals) == 1
        
        # Try to accept at turn 7 (expired)
        world.turn = 7
        accept_payload = ForeignPayload(
            source=DecisionSource.MINISTRY_ADVICE,
            action_type=ForeignActionType.ACCEPT_PROPOSAL,
            target_nation_id=proposer_id,
            parameters={"proposal_type": "ALLIANCE"}
        )
        execute_foreign(engine, target_id, accept_payload)
        
        # Should still be PEACE (proposal expired)
        assert world.relationship_matrix[proposer_id][target_id] == "PEACE"
        assert any("expired" in log.lower() for log in engine.logs)
    
    def test_clear_expired_proposals_removes_old(self):
        """clear_expired_proposals removes proposals older than 1 turn."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        
        proposer_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        target_nation = world.nations[target_id]
        
        # Add proposals at different turns
        target_nation.pending_proposals = [
            {"type": "ALLIANCE", "from": proposer_id, "turn": 3},
            {"type": "PEACE", "from": proposer_id, "turn": 5},
        ]
        
        # Current turn 6: turn 3 expired (>1 diff), turn 5 still valid
        world.turn = 6
        clear_expired_proposals(world)
        
        assert len(target_nation.pending_proposals) == 1
        assert target_nation.pending_proposals[0]["turn"] == 5
