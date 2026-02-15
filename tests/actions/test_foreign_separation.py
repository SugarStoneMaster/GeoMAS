
import pytest
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas import (
    ForeignProposal, ForeignIntent, ForeignIntentType
)
from geomas.actions.foreign import (
    ForeignProposalPayload, ProposalResponse, ForeignActionType, 
    ForeignResponseAction, ForeignPayload
)
from geomas.actions.foreign.handler import execute_foreign
from geomas.actions.common import Decision

class MockWorld:
    def __init__(self):
        self.nations = {}
        self.turn = 1
        self.trust_matrix = {}
        self.relationship_matrix = {}
        self.global_events = []

class MockEngine:
    def __init__(self):
        self.world = MockWorld()
        self.logs = []
        
    def adjust_trust(self, a, b, delta):
        if a not in self.world.trust_matrix: self.world.trust_matrix[a] = {}
        curr = self.world.trust_matrix[a].get(b, 50)
        self.world.trust_matrix[a][b] = curr + delta

def test_foreign_separation():
    engine = MockEngine()
    
    # Setup N1 and N2
    n1_id = "N1"
    n2_id = "N2"
    n3_id = "N3"
    
    # N1 has a pending proposal from N2
    engine.world.nations[n1_id] = type('Nation', (), {
        "pending_proposals": [{
            "id": "prop_123",
            "type": "ALLIANCE",
            "from": n2_id,
            "turn": 1,
            "message": "Ally?"
        }],
        "message_cooldown": {},
        "sent_proposals": []
    })
    engine.world.nations[n2_id] = type('Nation', (), {
        "pending_proposals": [],
        "message_cooldown": {},
        "sent_proposals": [{"id": "prop_123", "type": "ALLIANCE", "to": n1_id, "turn": 1, "status": "PENDING"}]
    })
    engine.world.nations[n3_id] = type('Nation', (), {
        "pending_proposals": [],
        "message_cooldown": {},
        "sent_proposals": []
    })
    
    # Setup Trust for active action
    engine.world.trust_matrix[n1_id] = {
        n2_id: 70,
        n3_id: 80
    }
    
    # Initialize Relationship Matrix
    engine.world.relationship_matrix[n1_id] = {n2_id: "PEACE", n3_id: "PEACE"}
    engine.world.relationship_matrix[n2_id] = {n1_id: "PEACE"}
    engine.world.relationship_matrix[n3_id] = {n1_id: "PEACE"}
    
    # Create Payload: Accept N2 AND Propose to N3
    payload = ForeignPayload(
        decision=Decision.APPROVE,
        proposal_responses=[
            ProposalResponse(
                proposal_id="prop_123",
                response=ForeignResponseAction.ACCEPT,
                message="Yes!"
            )
        ],
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=n3_id,
        message="Let's ally too!"
    )
    
    # Execute
    execute_foreign(engine, n1_id, payload)
    
    # Verify Responses
    # 1. Proposal from N2 should be removed (Accepted)
    assert len(engine.world.nations[n1_id].pending_proposals) == 0
    # 2. Alliance should be formed with N2
    assert engine.world.relationship_matrix[n1_id][n2_id] == "ALLIANCE"
    
    # Verify Active Action
    # 3. New Proposal should be sent to N3
    assert len(engine.world.nations[n3_id].pending_proposals) == 1
    assert engine.world.nations[n3_id].pending_proposals[0]["type"] == "ALLIANCE"
    
    print("\n✅ SUCCESS: Responses and Actions executed in parallel!")

if __name__ == "__main__":
    test_foreign_separation()
