import pytest
from geomas.schemas.world import WorldState, NationState, RelationshipState
from geomas.agents.context.input.foreign import ForeignInputBuilder
from geomas.actions.foreign.handler import respond_to_proposal
from geomas.actions.foreign.schemas import ProposalResponse, ForeignResponseAction
from geomas.actions.engine import ActionEngine

def test_diplomatic_fatigue_mechanics():
    """Verify trust penalty and opportunity filtering after rejection."""
    # 1. Setup world
    world = WorldState(turn=10)
    world.nations = {
        "VALKYR": NationState(id="VALKYR", name="Valkyr", color="#FF0000"),
        "OSTER": NationState(id="OSTER", name="Osterland", color="#00FF00")
    }
    # Set trust high enough to trigger opportunities
    world.trust_matrix = {"VALKYR": {"OSTER": 85.0}, "OSTER": {"VALKYR": 85.0}}
    world.relationship_matrix = {"VALKYR": {"OSTER": "PEACE"}, "OSTER": {"VALKYR": "PEACE"}}
    
    engine = ActionEngine(world)
    
    # 2. Simulate an alliance proposal from VALKYR to OSTER
    proposal_id = "test-123"
    world.nations["OSTER"].pending_proposals.append({
        "id": proposal_id,
        "type": "ALLIANCE",
        "from": "VALKYR",
        "turn": 9,
        "tier": "MUTUAL_DEFENSE"
    })
    world.nations["VALKYR"].sent_proposals.append({
        "id": proposal_id,
        "type": "ALLIANCE",
        "to": "OSTER",
        "turn": 9,
        "status": "PENDING"
    })
    
    # 3. Respond with REJECT
    response = ProposalResponse(proposal_id=proposal_id, response=ForeignResponseAction.REJECT)
    respond_to_proposal(engine, "OSTER", response)
    
    # Verify trust penalty (-5 from initial 85 = 80)
    assert world.trust_matrix["VALKYR"]["OSTER"] == 80.0
    assert world.trust_matrix["OSTER"]["VALKYR"] == 80.0
    
    # Verify status updated
    assert world.nations["VALKYR"].sent_proposals[0]["status"] == "REJECTED"
    assert world.nations["VALKYR"].sent_proposals[0]["resolved_turn"] == 10
    
    # 4. Check ForeignInputBuilder for Valkyr
    builder = ForeignInputBuilder(world)
    prompt = builder.build("VALKYR", 10)
    
    # Verify rejection note is in the prompt
    assert "(Wait for trust to improve or time to pass before retrying)" in prompt
    
    # Verify the "Strategic Opportunity" for OSTER is filtered out (Trust is 80, which usually triggers it)
    # The section should be completely missing if no other opportunities exist
    assert "## Strategic Opportunities (Treaties)" not in prompt
    
    # 5. Fast forward 11 turns (Turn 21) - Wait 11 to exceed the 10-turn cooldown
    world.turn = 21
    prompt_after_cooldown = builder.build("VALKYR", 21)
    
    # Verify opportunity is NOW back
    assert "## Strategic Opportunities (Treaties)" in prompt_after_cooldown
    opportunities_after = prompt_after_cooldown.split("## Strategic Opportunities (Treaties)")[1]
    assert "Osterland" in opportunities_after or "OSTER" in opportunities_after

if __name__ == "__main__":
    pytest.main([__file__])
