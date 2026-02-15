"""
Quick test to verify dynamic schema includes treaty_tier field.
"""
from geomas.agents.schemas import ForeignProposal
from geomas.agents.schemas.dynamic import get_dynamic_proposal_model
from geomas.actions.foreign.schemas import TreatyTier, ForeignActionType

# Create dynamic model
valid_ids = ["NAT_A", "NAT_B", "NAT_C"]
DynamicModel = get_dynamic_proposal_model(ForeignProposal, valid_ids)

# Check schema
print("=== Dynamic Foreign Proposal Schema ===")
print(DynamicModel.model_json_schema())

# Try to create an instance
from geomas.agents.schemas import ForeignIntent, ForeignIntentType
from geomas.actions.foreign.schemas import ForeignProposalPayload

try:
    proposal = DynamicModel(
        intent=ForeignIntent(
            public_intent=ForeignIntentType.COOPERATION,
            private_intent=ForeignIntentType.COOPERATION,
            reasoning="Test"
        ),
        payload=ForeignProposalPayload(
            action_type=ForeignActionType.PROPOSE_ALLIANCE,
            target_nation_id="NAT_B",
            treaty_tier=TreatyTier.MUTUAL_DEFENSE,
            message="Test alliance"
        )
    )
    print("\n✅ Successfully created proposal with treaty_tier!")
    print(f"Treaty tier: {proposal.payload.treaty_tier}")
except Exception as e:
    print(f"\n❌ Error: {e}")
