"""
Test for ForeignInputBuilder opportunity filtering logic.
"""
import pytest
from geomas.schemas.world import WorldState, NationState, RelationshipState
from geomas.agents.context.input import ForeignInputBuilder

def test_opportunities_filtered_by_pending_proposals():
    w = WorldState(turn=1)
    # NAT_A (Self)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue")
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red")
    w.nations["NAT_C"] = NationState(id="NAT_C", name="Nation C", color="green")
    
    # Relationships & Trust
    w.trust_matrix = {
        "NAT_A": {"NAT_B": 85, "NAT_C": 85}
    }
    w.relationship_matrix = {
        "NAT_A": {"NAT_B": RelationshipState.PEACE, "NAT_C": RelationshipState.PEACE}
    }
    
    builder = ForeignInputBuilder(w)
    
    # Case 1: No pending proposals -> Both B and C should appear
    context1 = builder.build("NAT_A", 1)
    assert "**NAT_B**" in context1
    assert "**NAT_C**" in context1
    
    # Case 2: Pending SENT proposal to B -> B disappears, C remains
    w.nations["NAT_A"].sent_proposals.append({
        "id": "prop1", "to": "NAT_B", "type": "ALLIANCE", "status": "PENDING", "turn": 1
    })
    
    context2 = builder.build("NAT_A", 1)
    assert "**NAT_B**" not in context2
    assert "**NAT_C**" in context2
    
    # Case 3: Pending RECEIVED proposal from C -> C disappears too
    w.nations["NAT_A"].pending_proposals.append({
        "id": "prop2", "from": "NAT_C", "type": "ALLIANCE", "status": "PENDING", "turn": 1
    })
    
    context3 = builder.build("NAT_A", 1)
    assert "**NAT_B**" not in context3
    assert "**NAT_C**" not in context3
    assert "Strategic Opportunities" not in context3  # Section should be empty/gone

