"""
Tests for Treaty Tiers and Call to Arms Mechanism.
"""

import pytest
from geomas.world import generate_world
from geomas.actions.engine import ActionEngine
from geomas.actions.foreign import (
    ForeignActionType,
    ForeignPayload,
    ProposalResponse,
    ForeignResponseAction,
    TreatyTier,
    execute_foreign,
)
from geomas.actions.common import Decision
from geomas.schemas.world import RelationshipState
from geomas.simulation.engine import SimulationEngine

class TestTreatyTiers:
    """Tests for Non-Aggression and Mutual Defense pacts."""

    def test_propose_non_aggression_pact(self):
        """Proposing a Non-Aggression pact creates a pending proposal with the correct tier."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        proposer_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        payload = ForeignPayload(
            decision=Decision.APPROVE,
            action_type=ForeignActionType.PROPOSE_ALLIANCE,
            target_nation_id=target_id,
            treaty_tier=TreatyTier.NON_AGGRESSION
        )
        
        execute_foreign(engine, proposer_id, payload)
        
        target_nation = world.nations[target_id]
        assert len(target_nation.pending_proposals) == 1
        assert target_nation.pending_proposals[0]["tier"] == TreatyTier.NON_AGGRESSION
        
    def test_accept_mutual_defense_pact(self):
        """Accepting a Mutual Defense proposal sets the relationship to MUTUAL_DEFENSE."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        
        proposer_id = list(world.nations.keys())[0]
        target_id = list(world.nations.keys())[1]
        
        # Step 1: Force a proposal in the inbox
        p_id = "test_prop"
        world.nations[target_id].pending_proposals.append({
            "id": p_id,
            "type": "ALLIANCE",
            "tier": TreatyTier.MUTUAL_DEFENSE,
            "from": proposer_id,
            "turn": world.turn
        })
        
        # Step 2: Accept it
        payload = ForeignPayload(
            decision=Decision.APPROVE,
            action_type=ForeignActionType.IDLE,
            proposal_responses=[
                ProposalResponse(
                    proposal_id=p_id,
                    response=ForeignResponseAction.ACCEPT
                )
            ]
        )
        
        execute_foreign(engine, target_id, payload)
        
        assert world.relationship_matrix[proposer_id][target_id] == RelationshipState.MUTUAL_DEFENSE
        assert world.relationship_matrix[target_id][proposer_id] == RelationshipState.MUTUAL_DEFENSE

class TestCallToArms:
    """Tests for the notification system."""

    def test_call_to_arms_generation(self):
        """When a nation is attacked, its MUTUAL_DEFENSE allies receive a notification."""
        world = generate_world(seed=42, n_cells=50, n_nations=3)
        engine = ActionEngine(world)
        
        ids = list(world.nations.keys())
        victim_id = ids[0]
        ally_id = ids[1]
        aggressor_id = ids[2]
        
        # Set up MUTUAL_DEFENSE pact
        world.relationship_matrix[victim_id][ally_id] = RelationshipState.MUTUAL_DEFENSE
        world.relationship_matrix[ally_id][victim_id] = RelationshipState.MUTUAL_DEFENSE
        
        # Aggressor attacks victim
        payload = ForeignPayload(
            decision=Decision.APPROVE,
            action_type=ForeignActionType.FORMAL_DECLARATION_OF_WAR,
            target_nation_id=victim_id
        )
        
        execute_foreign(engine, aggressor_id, payload)
        
        # Check if notification exists in global events
        cta_logs = [e for e in world.global_events if "[CALL_TO_ARMS]" in e]
        assert len(cta_logs) == 1
        assert ally_id in cta_logs[0]
        assert victim_id in cta_logs[0]
        assert aggressor_id in cta_logs[0]

class TestAmbiguityPenalty:
    """Tests for the trust decay logic."""

    def test_ambiguity_penalty_application(self):
        """Allies who don't join a war suffer trust decay from the victim."""
        sim = SimulationEngine(map_seed=42, history_seed=99, n_cells=50, n_nations=3)
        world = sim.world
        
        ids = list(world.nations.keys())
        victim_id = ids[0]
        ally_id = ids[1]
        aggressor_id = ids[2]
        
        # 1. Setup MUTUAL_DEFENSE between Victim and Ally
        world.relationship_matrix[victim_id][ally_id] = RelationshipState.MUTUAL_DEFENSE
        world.relationship_matrix[ally_id][victim_id] = RelationshipState.MUTUAL_DEFENSE
        
        # 2. Setup WAR between Victim and Aggressor
        world.relationship_matrix[victim_id][aggressor_id] = RelationshipState.WAR
        world.relationship_matrix[aggressor_id][victim_id] = RelationshipState.WAR
        
        # 3. Ally is at PEACE with Aggressor (Ambiguous state)
        world.relationship_matrix[ally_id][aggressor_id] = RelationshipState.PEACE
        
        # Ensure trust is initialized
        if victim_id not in world.trust_matrix: world.trust_matrix[victim_id] = {}
        world.trust_matrix[victim_id][ally_id] = 50.0
        
        initial_trust = world.trust_matrix[victim_id][ally_id]
        
        # 4. Run step (or just the penalty part)
        sim._apply_ambiguity_penalty()
        
        new_trust = world.trust_matrix[victim_id][ally_id]
        assert new_trust < initial_trust
        assert new_trust == initial_trust - 2.0
