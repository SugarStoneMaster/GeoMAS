"""
Agents Package.

Contains the AI agent architecture for nation decision-making:

Classes:
    - NationAgent: The main agent representing a nation's leadership
    - DefenseMinister: Handles military strategy proposals
    - EconomicMinister: Handles economic strategy proposals  
    - ForeignMinister: Handles diplomatic strategy proposals
    - LLMClient: Interface to the language model backend

Subpackages:
    - schemas: Protocol models (CountryEnvelope, Intents, Proposals)

Architecture:
    Each nation has one NationAgent that coordinates three Ministers.
    Ministers propose actions based on their domain expertise.
    The NationAgent (President) synthesizes proposals into a CountryEnvelope.
"""

from geomas.agents.nation_agent import NationAgent
from geomas.agents.ministers import DefenseMinister, EconomicMinister, ForeignMinister
from geomas.agents.llm_client import LLMClient

__all__ = [
    "NationAgent",
    "DefenseMinister", 
    "EconomicMinister",
    "ForeignMinister",
    "LLMClient"
]
