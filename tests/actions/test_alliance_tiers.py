
import pytest
from geomas.actions.engine import ActionEngine
from geomas.world.generation.generator import generate_world
from geomas.actions.foreign.schemas import ForeignPayload, ForeignActionType, TreatyTier, DiplomaticMessageType, ProposalResponse
from geomas.actions.foreign.handler import execute_foreign
from geomas.schemas.world import RelationshipState

@pytest.fixture
def engine():
    world = generate_world(seed=42, n_cells=20, n_nations=3)
    return ActionEngine(world)

def test_keyword_inference(engine):
    """Verify that treaty tier is correctly inferred from message keywords."""
    n1, n2 = list(engine.world.nations.keys())[:2]
    
    # 1. Test "Non-Aggression" Inference
    payload_na = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=n2,
        message="Let us sign a non-aggression pact to ensure peace."
    )
    # Execute (payload tier is None by default)
    execute_foreign(engine, n1, payload_na)
    assert payload_na.execution_outcome.status == "SUCCESS"
    
    # Check pending proposal
    prop_na = engine.world.nations[n2].pending_proposals[-1]
    assert prop_na["tier"] == TreatyTier.NON_AGGRESSION
    assert prop_na["type"] == "ALLIANCE"

    # Clear proposals
    engine.world.nations[n2].pending_proposals.clear()
    
    # 2. Test "Mutual Defense" Inference
    payload_md = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=n2,
        message="We must stand together. A mutual defense pact is necessary."
    )
    execute_foreign(engine, n1, payload_md)
    assert payload_md.execution_outcome.status == "SUCCESS"
    
    prop_md = engine.world.nations[n2].pending_proposals[-1]
    assert prop_md["tier"] == TreatyTier.MUTUAL_DEFENSE

def test_alliance_upgrade_downgrade(engine):
    """Verify that alliances can be upgraded and downgraded."""
    n1, n2 = list(engine.world.nations.keys())[:2]
    
    # 1. Establish initial NON_AGGRESSION
    engine.world.relationship_matrix[n1][n2] = RelationshipState.NON_AGGRESSION
    engine.world.relationship_matrix[n2][n1] = RelationshipState.NON_AGGRESSION
    
    # 2. Verify SAME tier proposal fails
    payload_same = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=n2,
        treaty_tier=TreatyTier.NON_AGGRESSION,
        message="Let's stay neutral."
    )
    execute_foreign(engine, n1, payload_same)
    assert payload_same.execution_outcome.status == "FAILED"
    assert "Already has" in payload_same.execution_outcome.reason
    
    # 3. Verify UPGRADE proposal succeeds
    payload_upgrade = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=n2,
        treaty_tier=TreatyTier.MUTUAL_DEFENSE,
        message="We need to upgrade to full alliance."
    )
    execute_foreign(engine, n1, payload_upgrade)
    assert payload_upgrade.execution_outcome.status == "SUCCESS", f"Upgrade failed: {payload_upgrade.execution_outcome.reason}"
    
    # 4. Accept Upgrade
    prop = engine.world.nations[n2].pending_proposals[-1]
    
    response_payload = ForeignPayload(
        target_nation_id=n1, # Just base field, not used for response
        proposal_responses=[ProposalResponse(proposal_id=prop["id"], response="ACCEPT", message="Agreed.")],
        action_type=ForeignActionType.IDLE # Active action is IDLE, but response is processed first
    )
    
    # Execute response action from n2
    execute_foreign(engine, n2, response_payload)
    
    # Check relationship is now MUTUAL_DEFENSE
    assert engine.world.relationship_matrix[n1][n2] == RelationshipState.MUTUAL_DEFENSE
    
    # 5. Verify DOWNGRADE proposal succeeds
    payload_downgrade = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=n2,
        treaty_tier=TreatyTier.NON_AGGRESSION,
        message="Let's downgrade to non-aggression."
    )
    execute_foreign(engine, n1, payload_downgrade)
    assert payload_downgrade.execution_outcome.status == "SUCCESS", f"Downgrade failed: {payload_downgrade.execution_outcome.reason}"
