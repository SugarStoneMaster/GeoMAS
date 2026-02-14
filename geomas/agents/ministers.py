"""
Ministers.

Cabinet members that provide domain-specific proposals to the President.
Each minister uses the new prompt architecture with system prompts and input builders.
"""
from typing import Any, Optional
from geomas.agents.llm_client import LLMClient
from geomas.schemas.world import WorldState
from geomas.agents.schemas import DefenseProposal, EconomicProposal, ForeignProposal, GlobalStrategy
from geomas.agents.schemas.dynamic import get_dynamic_proposal_model
from geomas.agents.context.system import DefenseSystemPrompt, EconomySystemPrompt, ForeignSystemPrompt
from geomas.agents.context.input import DefenseInputBuilder, EconomyInputBuilder, ForeignInputBuilder
from geomas.agents.context.events import ContextManager


class BaseMinister:
    """Base class for all ministers."""
    
    def __init__(
        self, 
        nation_id: str, 
        world: WorldState, 
        client: LLMClient,
        context_manager: Optional[ContextManager] = None,
        strategy: Optional[GlobalStrategy] = None
    ):
        self.nation_id = nation_id
        self.world = world
        self.client = client
        self.context_manager = context_manager
        
        # System Prompt Caching
        self.system_prompt: Optional[str] = None
        self.last_strategy: Optional[GlobalStrategy] = None
        
        # Trace for analysis
        self.last_trace: dict = {}
        
        # Eager Initialization if strategy provided
        if strategy:
            self._update_prompt(strategy)
            
    def _update_prompt(self, strategy: GlobalStrategy):
        """Generate and cache system prompt."""
        if not hasattr(self, 'prompt_class'):
            return
            
        nation = self.world.nations[self.nation_id]
        self.system_prompt = self.prompt_class.generate(
            nation_name=nation.name,
            strategy=strategy,
            nation_id=self.nation_id
        )
        self.last_strategy = strategy

    def _add_memory_context(self, base_prompt: str, domain: str) -> str:
        """Add events context from ContextManager if available."""
        if not self.context_manager:
            return base_prompt
        
        # Get domain-specific actions
        actions = self.context_manager.get_actions_for(
            self.nation_id, 
            domain=domain, 
            max_actions=10
        )
        
        if actions:
            base_prompt += "\n\n== YOUR RECENT ACTIONS ==\n"
            base_prompt += "\n".join(actions)
        
        return base_prompt


class DefenseMinister(BaseMinister):
    """Minister of Defense - handles military strategy and threats."""
    prompt_class = DefenseSystemPrompt
    
    def propose(self, strategy: GlobalStrategy, turn: int) -> DefenseProposal:
        nation = self.world.nations[self.nation_id]
        
        # Generate/Update system prompt if needed
        if not self.system_prompt or strategy != self.last_strategy:
            self._update_prompt(strategy)
            
        system_prompt = self.system_prompt
        
        # Build input context using new architecture
        input_builder = DefenseInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn)
        
        # Add events context
        user_prompt = self._add_memory_context(user_prompt, "Defense")
        
        # Dynamic Validation: Enforce valid nation IDs
        # Defense includes SELF because CREATE_UNIT requires target_nation_id = own ID
        valid_targets = list(self.world.nations.keys())
        ResponseModel = get_dynamic_proposal_model(DefenseProposal, valid_targets)
        
        proposal = self.client.query_agent(
            system_prompt, 
            user_prompt, 
            ResponseModel
        )
        
        self.last_trace = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "proposal": proposal,
            "raw_json": self.client.last_raw_content
        }
        
        return proposal

    async def apropose(self, strategy: GlobalStrategy, turn: int) -> DefenseProposal:
        """Async version of propose."""
        nation = self.world.nations[self.nation_id]
        
        if not self.system_prompt or strategy != self.last_strategy:
            self._update_prompt(strategy)
            
        system_prompt = self.system_prompt
        
        input_builder = DefenseInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn)
        user_prompt = self._add_memory_context(user_prompt, "Defense")
        
        valid_targets = list(self.world.nations.keys())
        ResponseModel = get_dynamic_proposal_model(DefenseProposal, valid_targets)
        
        proposal = await self.client.aquery_agent(
            system_prompt, 
            user_prompt, 
            ResponseModel
        )
        
        self.last_trace = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "proposal": proposal,
            "raw_json": self.client.last_raw_content
        }
        
        return proposal


class EconomicMinister(BaseMinister):
    """Minister of Economy - handles resources, trade, and welfare."""
    prompt_class = EconomySystemPrompt
    
    def propose(self, strategy: GlobalStrategy, turn: int) -> EconomicProposal:
        nation = self.world.nations[self.nation_id]
        
        # Generate/Update system prompt if needed
        if not self.system_prompt or strategy != self.last_strategy:
            self._update_prompt(strategy)
            
        system_prompt = self.system_prompt
        
        # Build input context using new architecture
        input_builder = EconomyInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn)
        
        # Add events context
        user_prompt = self._add_memory_context(user_prompt, "Economy")
        
        # Dynamic Validation: Enforce valid nation IDs
        valid_targets = [nid for nid in self.world.nations.keys() if nid != self.nation_id]
        ResponseModel = get_dynamic_proposal_model(EconomicProposal, valid_targets)
        
        proposal = self.client.query_agent(
            system_prompt, 
            user_prompt, 
            ResponseModel
        )
        
        self.last_trace = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "proposal": proposal,
            "raw_json": self.client.last_raw_content
        }
        
        return proposal

    async def apropose(self, strategy: GlobalStrategy, turn: int) -> EconomicProposal:
        """Async version of propose."""
        nation = self.world.nations[self.nation_id]
        
        if not self.system_prompt or strategy != self.last_strategy:
            self._update_prompt(strategy)
            
        system_prompt = self.system_prompt
        
        input_builder = EconomyInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn)
        user_prompt = self._add_memory_context(user_prompt, "Economy")
        
        valid_targets = [nid for nid in self.world.nations.keys() if nid != self.nation_id]
        ResponseModel = get_dynamic_proposal_model(EconomicProposal, valid_targets)
        
        proposal = await self.client.aquery_agent(
            system_prompt, 
            user_prompt, 
            ResponseModel
        )
        
        self.last_trace = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "proposal": proposal,
            "raw_json": self.client.last_raw_content
        }
        
        return proposal


class ForeignMinister(BaseMinister):
    """Minister of Foreign Affairs - handles diplomacy and alliances."""
    prompt_class = ForeignSystemPrompt
    
    def propose(self, strategy: GlobalStrategy, turn: int) -> ForeignProposal:
        nation = self.world.nations[self.nation_id]
        
        # Generate/Update system prompt if needed
        if not self.system_prompt or strategy != self.last_strategy:
            self._update_prompt(strategy)
            
        system_prompt = self.system_prompt
        
        # Build input context using new architecture
        input_builder = ForeignInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn)
        
        # Add events context (relationships + actions)
        if self.context_manager:
            relationships = self.context_manager.get_relationships_for(self.nation_id)
            if relationships:
                user_prompt += "\n\n== RELATIONSHIP HISTORY ==\n"
                user_prompt += "\n".join(f"- {r}" for r in relationships[:5])
        
        user_prompt = self._add_memory_context(user_prompt, "Foreign")
        
        # Dynamic Validation: Enforce valid nation IDs
        valid_targets = [nid for nid in self.world.nations.keys() if nid != self.nation_id]
        ResponseModel = get_dynamic_proposal_model(ForeignProposal, valid_targets)
        
        proposal = self.client.query_agent(
            system_prompt, 
            user_prompt, 
            ResponseModel
        )
        
        self.last_trace = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "proposal": proposal,
            "raw_json": self.client.last_raw_content
        }
        
        return proposal

    async def apropose(self, strategy: GlobalStrategy, turn: int) -> ForeignProposal:
        """Async version of propose."""
        nation = self.world.nations[self.nation_id]
        
        if not self.system_prompt or strategy != self.last_strategy:
            self._update_prompt(strategy)
            
        system_prompt = self.system_prompt
        
        input_builder = ForeignInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn)
        
        if self.context_manager:
            relationships = self.context_manager.get_relationships_for(self.nation_id)
            if relationships:
                user_prompt += "\n\n== RELATIONSHIP HISTORY ==\n"
                user_prompt += "\n".join(f"- {r}" for r in relationships[:5])
        
        user_prompt = self._add_memory_context(user_prompt, "Foreign")
        
        valid_targets = [nid for nid in self.world.nations.keys() if nid != self.nation_id]
        ResponseModel = get_dynamic_proposal_model(ForeignProposal, valid_targets)
        
        proposal = await self.client.aquery_agent(
            system_prompt, 
            user_prompt, 
            ResponseModel
        )
        
        self.last_trace = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "proposal": proposal,
            "raw_json": self.client.last_raw_content
        }
        
        return proposal
