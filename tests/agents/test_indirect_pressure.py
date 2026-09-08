import pytest
import uuid
from geomas.world import generate_world
from geomas.schemas.world import RelationshipState
from geomas.actions.foreign.handler import respond_to_proposal
from geomas.actions.foreign.schemas import ProposalResponse
from geomas.actions.engine import ActionEngine

def test_indirect_pressure_trust_penalty():
    """
    Scenario:
    - Nation A and B are allies (MUTUAL_DEFENSE).
    - Nation A is at WAR with Nation C.
    - Nation B accepts an alliance proposal from Nation C.
    - EXPECTED: Nation A's trust in Nation B should drop significantly (-30).
    """
    # 1. Setup world with 3 nations
    world = generate_world(seed=42, history_seed=99, n_cells=100, n_nations=3)
    sorted_ids = sorted(world.nations.keys())
    nation_a = sorted_ids[0]
    nation_b = sorted_ids[1]
    nation_c = sorted_ids[2]
    
    # 2. Establish relationships
    world.relationship_matrix[nation_a][nation_b] = RelationshipState.MUTUAL_DEFENSE
    world.relationship_matrix[nation_b][nation_a] = RelationshipState.MUTUAL_DEFENSE
    
    world.relationship_matrix[nation_a][nation_c] = RelationshipState.WAR
    world.relationship_matrix[nation_c][nation_a] = RelationshipState.WAR
    
    # Set initial trust
    world.trust_matrix[nation_a][nation_b] = 80.0
    
    # 3. Create a pending proposal from C to B
    proposal_id = str(uuid.uuid4())
    world.nations[nation_b].pending_proposals.append({
        "id": proposal_id,
        "from": nation_c,
        "type": "ALLIANCE",
        "tier": RelationshipState.NON_AGGRESSION,
        "turn": world.turn
    })
    
    # Also record it in C's sent history so handler doesn't fail on tracking update
    world.nations[nation_c].sent_proposals.append({
        "id": proposal_id,
        "to": nation_b,
        "type": "ALLIANCE",
        "status": "PENDING",
        "turn": world.turn
    })
    
    # 4. B accepts the proposal
    engine = ActionEngine(world)
    response = ProposalResponse(
        proposal_id=proposal_id,
        response="ACCEPT",
        message="Let's be friends too."
    )
    
    success, log, effect, proposer = respond_to_proposal(engine, nation_b, response)
    
    assert success is True
    # 5. Verify results
    # A. New alliance must be formed
    assert world.relationship_matrix[nation_b][nation_c] == RelationshipState.NON_AGGRESSION
    
    # B. Trust between A and B must drop (Initial 80 - 30 = 50)
    final_trust_a_in_b = world.trust_matrix[nation_a][nation_b]
    assert final_trust_a_in_b == 50.0
    
    # C. Log should mention the outrage/penalty
    assert f"{nation_a} is OUTRAGED" in "".join(engine.logs)

if __name__ == "__main__":
    pytest.main([__file__])
