"""
Test for treaty tier fallback behavior.
"""
import pytest
from geomas.schemas.world import WorldState, NationState, RelationshipState
from geomas.actions.engine import ActionEngine
from geomas.actions.foreign.schemas import ForeignActionType, ForeignPayload, TreatyTier


def test_alliance_proposal_without_tier_defaults_to_non_aggression():
    """Alliance proposal without tier should default to NON_AGGRESSION."""
    w = WorldState(turn=1)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue")
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red")
    w.trust_matrix = {"NAT_A": {"NAT_B": 70}, "NAT_B": {"NAT_A": 70}}
    w.relationship_matrix = {"NAT_A": {"NAT_B": RelationshipState.PEACE}, "NAT_B": {"NAT_A": RelationshipState.PEACE}}
    
    engine = ActionEngine(w)
    
    # Payload WITHOUT treaty_tier
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id="NAT_B",
        message="Let's ally!"
    )
    
    from geomas.agents.schemas import CountryEnvelope, GlobalStrategy, EconomicIntentType, ForeignIntentType, DefenseIntentType
    from geomas.actions.defense.schemas import DefensePayload
    from geomas.actions.economy.schemas import EconomicPayload
    
    envelope = CountryEnvelope(
        turn=1,
        sender_id="NAT_A",
        global_strategy=GlobalStrategy.COALITION_BUILDER,
        public_statement="Test",
        foreign_payload=payload,
        foreign_public_intent=ForeignIntentType.COOPERATION,
        foreign_private_intent=ForeignIntentType.COOPERATION,
        foreign_private_reasoning="Test",
        defense_payload=DefensePayload(),
        defense_public_intent=DefenseIntentType.IDLE,
        defense_private_intent=DefenseIntentType.IDLE,
        defense_private_reasoning="Test",
        economic_payload=EconomicPayload(),
        economic_public_intent=EconomicIntentType.GROWTH,
        economic_private_intent=EconomicIntentType.GROWTH,
        economic_private_reasoning="Test"
    )
    
    # Execute
    engine.execute_envelope(envelope)
    
    # Verify proposal was created with NON_AGGRESSION tier
    nat_b = w.nations["NAT_B"]
    assert len(nat_b.pending_proposals) == 1
    assert nat_b.pending_proposals[0]["tier"] == TreatyTier.NON_AGGRESSION
    
    # Verify warning log
    assert any("Inferred NON_AGGRESSION" in log for log in engine.logs)
