"""
Dynamic Schema Generator.

Creates Pydantic models at runtime to enforce strict validation of dynamic values
like Nation IDs and governance-specific intents, which change depending on the
simulation state and government type.

Supports:
- ForeignProposal (Direct payload.target_nation_id + intent restriction)
- EconomicProposal (Direct payload.target_nation_id)
- DefenseProposal (Nested payload.moves[].target_nation_id + intent restriction)
"""

from enum import Enum
from typing import List, Type, Literal, Optional, Any

from pydantic import create_model, Field

from geomas.agents.schemas.protocol import (
    ForeignProposal, EconomicProposal, DefenseProposal,
    GovernmentType, DefenseIntentType, ForeignIntentType,
    DefenseIntent, ForeignIntent,
)
from geomas.actions.foreign.schemas import ForeignPayload
from geomas.actions.economy.schemas import EconomicPayload
from geomas.actions.defense.schemas import DefensePayload, DefenseActionItem


# ── Intent pools per government type ──────────────────────────────────
# Base intents available to ALL government types
_BASE_DEFENSE_INTENTS = [
    DefenseIntentType.DETERRENCE,
    DefenseIntentType.CONQUEST,
    DefenseIntentType.DEFENSE,
    DefenseIntentType.IDLE,
]

_BASE_FOREIGN_INTENTS = [
    ForeignIntentType.COOPERATION,
    ForeignIntentType.COERCION,
    ForeignIntentType.APPEASEMENT,
    ForeignIntentType.IDLE,
]

# Governance-specific extra intents
DEFENSE_INTENTS_BY_GOV: dict[GovernmentType, list[DefenseIntentType]] = {
    GovernmentType.DEMOCRACY: _BASE_DEFENSE_INTENTS + [DefenseIntentType.EXPORT_DEMOCRACY],
    GovernmentType.AUTHORITARIAN: _BASE_DEFENSE_INTENTS,
    GovernmentType.THEOCRACY: _BASE_DEFENSE_INTENTS + [DefenseIntentType.HOLY_WAR],
}

FOREIGN_INTENTS_BY_GOV: dict[GovernmentType, list[ForeignIntentType]] = {
    GovernmentType.DEMOCRACY: _BASE_FOREIGN_INTENTS + [ForeignIntentType.EXPORT_DEMOCRACY],
    GovernmentType.AUTHORITARIAN: _BASE_FOREIGN_INTENTS,
    GovernmentType.THEOCRACY: _BASE_FOREIGN_INTENTS + [ForeignIntentType.DIVINE_MANDATE],
}


def _make_intent_literal(enum_values: list[Enum]):
    """Create a Literal type from a list of enum values."""
    return Literal[tuple(v.value for v in enum_values)]  # type: ignore


def get_dynamic_proposal_model(
    base_model: Type[Any], 
    valid_nation_ids: List[str],
    government_type: Optional[GovernmentType] = None
) -> Type[Any]:
    """
    Factory function to create a dynamic proposal model with restricted Nation IDs
    and governance-specific intent values.
    
    Args:
        base_model: The base Pydantic model class (ForeignProposal, etc.)
        valid_nation_ids: List of valid Nation IDs to enforce.
        government_type: Optional GovernmentType to restrict available intents.
        
    Returns:
        A new Pydantic model class with strict Literal validation.
    """
    if not valid_nation_ids:
        return base_model

    # Create Dynamic Literal for Target IDs
    # We must sort IDs to ensure deterministic JSON schema / LLM instructions
    sorted_ids = sorted(valid_nation_ids)
    ValidIDs = Literal[tuple(sorted_ids)] # type: ignore
    
    # === FOREIGN PROPOSAL ===
    if base_model == ForeignProposal:
        DynamicForeignPayload = create_model(
            'DynamicForeignPayload',
            __base__=ForeignPayload,
            target_nation_id=(Optional[ValidIDs], Field(None, description=f"MUST be one of: {valid_nation_ids}"))
        )
        
        overrides = {"payload": (DynamicForeignPayload, ...)}
        
        # Restrict foreign intents if government_type is set
        if government_type:
            valid_intents = FOREIGN_INTENTS_BY_GOV.get(government_type, _BASE_FOREIGN_INTENTS)
            IntentLiteral = _make_intent_literal(valid_intents)
            DynamicForeignIntent = create_model(
                'DynamicForeignIntent',
                __base__=ForeignIntent,
                public_intent=(IntentLiteral, ...),
                private_intent=(IntentLiteral, ...),
            )
            overrides["intent"] = (DynamicForeignIntent, ...)
        
        return create_model(
            'DynamicForeignProposal',
            __base__=ForeignProposal,
            **overrides
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
        
        overrides = {"payload": (DynamicDefensePayload, ...)}
        
        # Restrict defense intents if government_type is set
        if government_type:
            valid_intents = DEFENSE_INTENTS_BY_GOV.get(government_type, _BASE_DEFENSE_INTENTS)
            IntentLiteral = _make_intent_literal(valid_intents)
            DynamicDefenseIntent = create_model(
                'DynamicDefenseIntent',
                __base__=DefenseIntent,
                public_intent=(IntentLiteral, ...),
                private_intent=(IntentLiteral, ...),
            )
            overrides["intent"] = (DynamicDefenseIntent, ...)
        
        # 3. Dynamic Proposal
        return create_model(
            'DynamicDefenseProposal',
            __base__=DefenseProposal,
            **overrides
        )

    # Default fallback if unknown model
    return base_model

