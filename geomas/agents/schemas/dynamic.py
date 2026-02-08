"""
Dynamic Schema Generator.

Creates Pydantic models at runtime to enforce strict validation of dynamic values
like Nation IDs, which change depending on the simulation state.
"""

from typing import List, Type, Literal, Optional
from pydantic import create_model, Field
from geomas.agents.schemas import ForeignProposal, ForeignPayload
from geomas.actions.foreign.schemas import ForeignActionType, DiplomaticMessageType
from geomas.actions.common import Decision

def get_dynamic_foreign_proposal(valid_nation_ids: List[str]) -> Type[ForeignProposal]:
    """
    Create a ForeignProposal model that strictly validates target_nation_id
    against the provided list of valid IDs using a Literal type.
    """
    if not valid_nation_ids:
        return ForeignProposal

    # Create Dynamic Literal for Target IDs
    # We must convert to tuple for Literal
    ValidIDs = Literal[tuple(valid_nation_ids)] # type: ignore
    
    # 1. Create Dynamic Payload
    # We redefine ForeignPayload but with restricted target_nation_id
    DynamicForeignPayload = create_model(
        'DynamicForeignPayload',
        decision=(Decision, Field(default=Decision.PENDING, description="FOR PRESIDENT ONLY. Ministers MUST leave as PENDING.")),
        action_type=(Optional[ForeignActionType], None),
        target_nation_id=(Optional[ValidIDs], Field(None, description=f"MUST be one of: {valid_nation_ids}")),
        message=(Optional[str], Field(None, description="Diplomatic message to the target nation.")),
        diplomatic_message_type=(Optional[DiplomaticMessageType], Field(None, description="Required for SEND_DIPLOMATIC_MESSAGE.")),
        proposal_ref_type=(Optional[str], None),
        __base__=ForeignPayload
    )
    
    # 2. Create Dynamic Proposal
    # We redefine ForeignProposal to use the Dynamic Payload
    DynamicForeignProposal = create_model(
        'DynamicForeignProposal',
        payload=(DynamicForeignPayload, ...),
        __base__=ForeignProposal
    )
    
    return DynamicForeignProposal
