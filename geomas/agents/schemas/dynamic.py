"""
Dynamic Schema Generator.

Creates Pydantic models at runtime to enforce strict validation of dynamic values
like Nation IDs, which change depending on the simulation state.

Supports:
- ForeignProposal (Direct payload.target_nation_id)
- EconomicProposal (Direct payload.target_nation_id)
- DefenseProposal (Nested payload.moves[].target_nation_id)
"""

from typing import List, Type, Literal, Optional, Any
from pydantic import create_model, Field

from geomas.agents.schemas import ForeignProposal, EconomicProposal, DefenseProposal
from geomas.actions.foreign.schemas import ForeignPayload
from geomas.actions.economy.schemas import EconomicPayload
from geomas.actions.defense.schemas import DefensePayload, DefenseActionItem

def get_dynamic_proposal_model(
    base_model: Type[Any], 
    valid_nation_ids: List[str]
) -> Type[Any]:
    """
    Factory function to create a dynamic proposal model with restricted Nation IDs.
    Automatically detects the model type and applies the appropriate constraints.
    
    Args:
        base_model: The base Pydantic model class (ForeignProposal, etc.)
        valid_nation_ids: List of valid Nation IDs to enforce.
        
    Returns:
        A new Pydantic model class with strict Literal validation.
    """
    if not valid_nation_ids:
        return base_model

    # Create Dynamic Literal for Target IDs
    # We must convert to tuple for Literal to work in pydantic
    ValidIDs = Literal[tuple(valid_nation_ids)] # type: ignore
    
    # === FOREIGN PROPOSAL ===
    if base_model == ForeignProposal:
        DynamicForeignPayload = create_model(
            'DynamicForeignPayload',
            __base__=ForeignPayload,
            target_nation_id=(Optional[ValidIDs], Field(None, description=f"MUST be one of: {valid_nation_ids}"))
        )
        return create_model(
            'DynamicForeignProposal',
            __base__=ForeignProposal,
            payload=(DynamicForeignPayload, ...)
        )

    # === ECONOMIC PROPOSAL ===
    elif base_model == EconomicProposal:
        DynamicEconomicPayload = create_model(
            'DynamicEconomicPayload',
            __base__=EconomicPayload,
            target_nation_id=(Optional[ValidIDs], Field(None, description=f"MUST be one of: {valid_nation_ids}"))
        )
        return create_model(
            'DynamicEconomicProposal',
            __base__=EconomicProposal,
            payload=(DynamicEconomicPayload, ...)
        )

    # === DEFENSE PROPOSAL ===
    elif base_model == DefenseProposal:
        # Defense is trickier: target_nation_id is inside a List[DefenseActionItem]
        
        # 1. Dynamic Action Item
        DynamicDefenseActionItem = create_model(
            'DynamicDefenseActionItem',
            __base__=DefenseActionItem,
            target_nation_id=(Optional[ValidIDs], Field(None, description=f"MUST be one of: {valid_nation_ids}"))
        )
        
        # 2. Dynamic Payload using the Dynamic Action Item
        DynamicDefensePayload = create_model(
            'DynamicDefensePayload',
            __base__=DefensePayload,
            moves=(List[DynamicDefenseActionItem], Field(
                default_factory=list, 
                max_length=3,
                description="Ordered list of actions (Waterfall Logic). MAXIMUM 3 ACTIONS ALLOWED."
            ))
        )
        
        # 3. Dynamic Proposal
        return create_model(
            'DynamicDefenseProposal',
            __base__=DefenseProposal,
            payload=(DynamicDefensePayload, ...)
        )

    # Default fallback if unknown model
    return base_model
