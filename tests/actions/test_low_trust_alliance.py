import pytest
from geomas.schemas.world import WorldState, NationState
from geomas.actions.engine import ActionEngine
from geomas.actions.foreign.schemas import ForeignActionType, ForeignPayload, TreatyTier
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy, ForeignIntentType, DefenseIntentType
from geomas.actions.defense.schemas import DefensePayload
from geomas.actions.economy.schemas import EconomicPayload

def test_low_trust_alliance_allowed():
    # Setup world with low trust (e.g. 10)
    w = WorldState(turn=1)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue")
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red")
    w.trust_matrix = {"NAT_A": {"NAT_B": 10}, "NAT_B": {"NAT_A": 10}}
    w.relationship_matrix = {"NAT_A": {"NAT_B": "PEACE"}, "NAT_B": {"NAT_A": "PEACE"}}
    
    engine = ActionEngine(w)
    
    # Payload for Alliance Proposal
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id="NAT_B",
        message="Ally?",
        treaty_tier=TreatyTier.MUTUAL_DEFENSE
    )
    
    # Create envelope
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
    )
    
    # Execute
    engine.execute_envelope(envelope)
    
    # Assert
    # Should be successful (status="SUCCESS" in outcome, or proposal pending in target)
    nat_b = w.nations["NAT_B"]
    assert len(nat_b.pending_proposals) == 1
    assert nat_b.pending_proposals[0]["type"] == "ALLIANCE"
    assert payload.execution_outcome.status == "SUCCESS"
    
    # 2. Accept Proposal (to trigger log)
    # Simulate Target accepting
    from geomas.actions.foreign.handler import respond_to_proposal
    from geomas.actions.foreign.schemas import ProposalResponse, ForeignResponseAction
    
    proposal_id = nat_b.pending_proposals[0]["id"]
    response = ProposalResponse(
        proposal_id=proposal_id,
        response=ForeignResponseAction.ACCEPT,
        message="Let's risk it!"
    )
    
    respond_to_proposal(engine, "NAT_B", response)
    
    # Assert Logs
    found_target_risk = False
    found_proposer_risk = False
    
    for log in engine.logs:
        if "RISKY treaty for NAT_B" in log and "10 < 50" in log:
            found_target_risk = True
        if "RISKY treaty for NAT_A" in log and "10 < 50" in log:
            found_proposer_risk = True
            
    assert found_target_risk, f"Target risk log not found in: {engine.logs}"
    assert found_proposer_risk, f"Proposer risk log not found in: {engine.logs}"
