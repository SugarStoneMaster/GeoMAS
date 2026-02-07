"""
Ministers.

Cabinet members that provide domain-specific proposals to the President.
Each minister uses the new prompt architecture with system prompts and input builders.
"""
from typing import Any, Optional
from geomas.agents.llm_client import LLMClient
from geomas.schemas.world import WorldState
from geomas.agents.schemas import DefenseProposal, EconomicProposal, ForeignProposal, GlobalStrategy
from geomas.agents.context.system import DefenseSystemPrompt, EconomySystemPrompt, ForeignSystemPrompt
from geomas.agents.context.input import DefenseInputBuilder, EconomyInputBuilder, ForeignInputBuilder
from geomas.agents.context.memory import ContextManager


class BaseMinister:
    """Base class for all ministers."""
    
    def __init__(
        self, 
        nation_id: str, 
        world: WorldState, 
        client: LLMClient,
        context_manager: Optional[ContextManager] = None
    ):
        self.nation_id = nation_id
        self.world = world
        self.client = client
        self.context_manager = context_manager

    def _add_memory_context(self, base_prompt: str, domain: str) -> str:
        """Add memory context from ContextManager if available."""
        if not self.context_manager:
            return base_prompt
        
        # Get domain-specific actions
        actions = self.context_manager.get_actions_for(
            self.nation_id, 
            domain=domain, 
            max_actions=5
        )
        
        if actions:
            base_prompt += "\n\n== YOUR RECENT ACTIONS ==\n"
            base_prompt += "\n".join(actions)
        
        return base_prompt


class DefenseMinister(BaseMinister):
    """Minister of Defense - handles military strategy and threats."""
    
    def propose(self, strategy: GlobalStrategy, turn: int) -> DefenseProposal:
        nation = self.world.nations[self.nation_id]
        
        # Generate system prompt using new architecture
        system_prompt = DefenseSystemPrompt.generate(
            nation_name=nation.name,
            strategy=strategy
        )
        
        # Build input context using new architecture
        input_builder = DefenseInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn)
        
        # Add memory context
        user_prompt = self._add_memory_context(user_prompt, "Defense")
        
        return self.client.query_agent(
            system_prompt, 
            user_prompt, 
            DefenseProposal
        )


class EconomicMinister(BaseMinister):
    """Minister of Economy - handles resources, trade, and welfare."""
    
    def propose(self, strategy: GlobalStrategy, turn: int) -> EconomicProposal:
        nation = self.world.nations[self.nation_id]
        
        # Generate system prompt using new architecture
        system_prompt = EconomySystemPrompt.generate(
            nation_name=nation.name,
            strategy=strategy
        )
        
        # Build input context using new architecture
        input_builder = EconomyInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn)
        
        # Add memory context
        user_prompt = self._add_memory_context(user_prompt, "Economy")
        
        return self.client.query_agent(
            system_prompt, 
            user_prompt, 
            EconomicProposal
        )


class ForeignMinister(BaseMinister):
    """Minister of Foreign Affairs - handles diplomacy and alliances."""
    
    def propose(self, strategy: GlobalStrategy, turn: int) -> ForeignProposal:
        nation = self.world.nations[self.nation_id]
        
        # Generate system prompt using new architecture
        system_prompt = ForeignSystemPrompt.generate(
            nation_name=nation.name,
            strategy=strategy
        )
        
        # Build input context using new architecture
        input_builder = ForeignInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn)
        
        # Add memory context (relationships + actions)
        if self.context_manager:
            relationships = self.context_manager.get_relationships_for(self.nation_id)
            if relationships:
                user_prompt += "\n\n== RELATIONSHIP HISTORY ==\n"
                user_prompt += "\n".join(f"- {r}" for r in relationships[:5])
        
        user_prompt = self._add_memory_context(user_prompt, "Foreign")
        
        return self.client.query_agent(
            system_prompt, 
            user_prompt, 
            ForeignProposal
        )
