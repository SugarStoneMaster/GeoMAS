"""
Context Package for LLM Agents.

Provides translators and generators that convert world state into natural language
suitable for LLM agent consumption.

Modules:
    - spatial: Geographic/strategic intelligence (SpatialTranslator)
    - profile: Nation identity and relationships (NationProfileGenerator)
    - military: Dynamic military state (MilitaryTranslator)

Usage:
    from geomas.agents.context import SpatialTranslator, NationProfileGenerator, MilitaryTranslator
    
    translator = SpatialTranslator(world)
    report = translator.generate_intelligence_report(nation_id)
    
    profile_gen = NationProfileGenerator(world, genesis_db)
    profile = profile_gen.generate_profile(nation_id, strategy)
    
    military = MilitaryTranslator(world)
    mil_report = military.generate_military_report(nation_id)
"""

from geomas.agents.context.spatial import SpatialTranslator
from geomas.agents.context.profile import NationProfileGenerator
from geomas.agents.context.military import MilitaryTranslator

__all__ = [
    "SpatialTranslator",
    "NationProfileGenerator",
    "MilitaryTranslator",
]
