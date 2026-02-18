"""
Test for smart treaty tier fallback behavior based on message content.
"""
import pytest
from geomas.schemas.world import WorldState, NationState, RelationshipState
from geomas.actions.engine import ActionEngine
from geomas.actions.foreign.schemas import ForeignActionType, ForeignPayload, TreatyTier
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy, ForeignIntentType, DefenseIntentType
from geomas.actions.defense.schemas import DefensePayload
from geomas.actions.economy.schemas import EconomicPayload


def create_envelope(sender_id, payload):
    return CountryEnvelope(
        turn=1,
        sender_id=sender_id,
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
    )

def test_fallback_infers_mutual_defense_from_message():
    """Alliance proposal missing tier but mentioning 'mutual defense' should default to MUTUAL_DEFENSE."""
    w = WorldState(turn=1)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue")
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red")
    w.trust_matrix = {"NAT_A": {"NAT_B": 80}, "NAT_B": {"NAT_A": 80}}
    w.relationship_matrix = {"NAT_A": {"NAT_B": RelationshipState.PEACE}, "NAT_B": {"NAT_A": RelationshipState.PEACE}}
    
    engine = ActionEngine(w)
    
    # Payload WITHOUT treaty_tier but WITH specific message
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id="NAT_B",
        message="We should sign a mutual defense pact to protect our people."
    )
    
    envelope = create_envelope("NAT_A", payload)
    engine.execute_envelope(envelope)
    
    # Verify inference
    nat_b = w.nations["NAT_B"]
    assert len(nat_b.pending_proposals) == 1
    assert nat_b.pending_proposals[0]["tier"] == TreatyTier.MUTUAL_DEFENSE
    
    # Verify log
    assert any("Inferred MUTUAL_DEFENSE" in log for log in engine.logs)

def test_fallback_defaults_to_non_aggression_for_generic_message():
    """Alliance proposal missing tier with generic message defaults to NON_AGGRESSION."""
    w = WorldState(turn=1)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue")
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red")
    w.trust_matrix = {"NAT_A": {"NAT_B": 70}, "NAT_B": {"NAT_A": 70}}
    
    engine = ActionEngine(w)
    
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id="NAT_B",
        message="Let's form an alliance."
    )
    
    envelope = create_envelope("NAT_A", payload)
    engine.execute_envelope(envelope)
    
    # Verify default
    nat_b = w.nations["NAT_B"]
    assert len(nat_b.pending_proposals) == 1
    assert nat_b.pending_proposals[0]["tier"] == TreatyTier.NON_AGGRESSION
    
    # Verify log
    assert any("Inferred NON_AGGRESSION" in log for log in engine.logs)

def test_context_builder_suggests_opportunities():
    """Verify ForeignInputBuilder suggests specific treaty upgrades."""
    from geomas.agents.context.input import ForeignInputBuilder
    
    w = WorldState(turn=1)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue")
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red")
    w.nations["NAT_C"] = NationState(id="NAT_C", name="Nation C", color="green")
    
    # NAT_B: High Trust -> Mutual Defense
    w.trust_matrix = {
        "NAT_A": {"NAT_B": 85, "NAT_C": 65}
    }
    w.relationship_matrix = {
        "NAT_A": {"NAT_B": RelationshipState.PEACE, "NAT_C": RelationshipState.PEACE}
    }
    
    builder = ForeignInputBuilder(w)
    context = builder.build("NAT_A", 1)
    
    print(context)
    
    assert "## Strategic Opportunities (Treaties)" in context
    assert "NAT_B" in context and "MUTUAL_DEFENSE" in context
    assert "NAT_C" in context and "NON_AGGRESSION" in context
