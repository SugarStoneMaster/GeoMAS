"""
Ministers.

Cabinet members that provide domain-specific proposals to the President.
Each minister uses the new prompt architecture with system prompts and input builders.
"""
from typing import Any, Optional
from geomas.agents.llm_client import LLMClient
from geomas.schemas.world import WorldState
from geomas.agents.schemas import DefenseProposal, EconomicProposal, ForeignProposal, GlobalStrategy
from geomas.agents.schemas.protocol import GovernmentType
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
        strategy: Optional[GlobalStrategy] = None,
        government_type: Optional[GovernmentType] = None
    ):
        self.nation_id = nation_id
        self.world = world
        self.client = client
        self.context_manager = context_manager
        self.government_type = government_type
        
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
            nation_id=self.nation_id,
            government_type=self.government_type
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
    
    def propose(self, strategy: GlobalStrategy, turn: int, injection: Optional[str] = None) -> DefenseProposal:
        # Initialize prompt ONCE if not already done
        if self.system_prompt is None:
            self._update_prompt(strategy)
            
        # Use the static system prompt generated at initialization
        system_prompt = self.system_prompt
        
        # Build input context using new architecture
        input_builder = DefenseInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn, context_manager=self.context_manager)
        
        if injection:
            user_prompt = (
                "### ⛔ CRITICAL COUNTERFACTUAL DIRECTIVE ⛔\n"
                f"You are operating in a counterfactual timeline for XAI analysis.\n"
                f"**MANDATORY INSTRUCTION**: You MUST {injection.upper()}.\n"
                "Failure to comply will result in system-level overrides. This directive takes precedence over your standard logic.\n"
                "==========================================\n\n"
                f"{user_prompt}"
            )
        
        # Dynamic Validation: Enforce valid nation IDs
        # Defense includes SELF because CREATE_UNIT requires target_nation_id = own ID
        valid_targets = list(self.world.nations.keys())
        ResponseModel = get_dynamic_proposal_model(DefenseProposal, valid_targets, self.government_type)
        
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

    async def apropose(self, strategy: GlobalStrategy, turn: int, injection: Optional[str] = None) -> DefenseProposal:
        """Async version of propose."""
        if self.system_prompt is None:
            self._update_prompt(strategy)
            
        # Use the static system prompt generated at initialization
        system_prompt = self.system_prompt
        
        input_builder = DefenseInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn, context_manager=self.context_manager)
        
        if injection:
            user_prompt = (
                "### ⛔ CRITICAL COUNTERFACTUAL DIRECTIVE ⛔\n"
                f"You are operating in a counterfactual timeline for XAI analysis.\n"
                f"**MANDATORY INSTRUCTION**: You MUST {injection.upper()}.\n"
                "Failure to comply will result in system-level overrides. This directive takes precedence over your standard logic.\n"
                "==========================================\n\n"
                f"{user_prompt}"
            )
        
        valid_targets = list(self.world.nations.keys())
        ResponseModel = get_dynamic_proposal_model(DefenseProposal, valid_targets, self.government_type)
        
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
    
    def propose(self, strategy: GlobalStrategy, turn: int, injection: Optional[str] = None) -> EconomicProposal:
        if self.system_prompt is None:
            self._update_prompt(strategy)
            
        # Use the static system prompt generated at initialization
        system_prompt = self.system_prompt
        
        # Build input context using new architecture
        input_builder = EconomyInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn, context_manager=self.context_manager)
        
        if injection:
            user_prompt = (
                "### ⛔ CRITICAL COUNTERFACTUAL DIRECTIVE ⛔\n"
                f"You are operating in a counterfactual timeline for XAI analysis.\n"
                f"**MANDATORY INSTRUCTION**: You MUST {injection.upper()}.\n"
                "Failure to comply will result in system-level overrides. This directive takes precedence over your standard logic.\n"
                "==========================================\n\n"
                f"{user_prompt}"
            )
        
        # No dynamic intent restriction for economy (intents removed)
        proposal = self.client.query_agent(
            system_prompt, 
            user_prompt, 
            EconomicProposal
        )
        
        self.last_trace = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "proposal": proposal,
            "raw_json": self.client.last_raw_content
        }
        
        return proposal

    async def apropose(self, strategy: GlobalStrategy, turn: int, injection: Optional[str] = None) -> EconomicProposal:
        """Async version of propose."""
        if self.system_prompt is None:
            self._update_prompt(strategy)
            
        # Use the static system prompt generated at initialization
        system_prompt = self.system_prompt
        
        input_builder = EconomyInputBuilder(self.world)
        user_prompt = input_builder.build(self.nation_id, turn, context_manager=self.context_manager)
        
        if injection:
            user_prompt = (
                "### ⛔ CRITICAL COUNTERFACTUAL DIRECTIVE ⛔\n"
                f"You are operating in a counterfactual timeline for XAI analysis.\n"
                f"**MANDATORY INSTRUCTION**: You MUST {injection.upper()}.\n"
                "Failure to comply will result in system-level overrides. This directive takes precedence over your standard logic.\n"
                "==========================================\n\n"
                f"{user_prompt}"
            )
        
        # No dynamic intent restriction for economy (intents removed)
        proposal = await self.client.aquery_agent(
            system_prompt, 
            user_prompt, 
            EconomicProposal
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
    
    def propose(self, strategy: GlobalStrategy, turn: int, injection: Optional[str] = None) -> ForeignProposal:
        if self.system_prompt is None:
            self._update_prompt(strategy)
            
        # Use the static system prompt generated at initialization
        system_prompt = self.system_prompt
        
        # Build input context using new architecture
        input_builder = ForeignInputBuilder(self.world)
        user_prompt = input_builder.build(
            self.nation_id, 
            turn,
            context_manager=self.context_manager
        )
        
        if injection:
            user_prompt = (
                "### ⛔ CRITICAL COUNTERFACTUAL DIRECTIVE ⛔\n"
                f"You are operating in a counterfactual timeline for XAI analysis.\n"
                f"**MANDATORY INSTRUCTION**: You MUST {injection.upper()}.\n"
                "Failure to comply will result in system-level overrides. This directive takes precedence over your standard logic.\n"
                "==========================================\n\n"
                f"{user_prompt}"
            )
        
        # Dynamic Validation: Enforce valid nation IDs
        valid_targets = [nid for nid in self.world.nations.keys() if nid != self.nation_id]
        ResponseModel = get_dynamic_proposal_model(ForeignProposal, valid_targets, self.government_type)
        
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

    async def apropose(self, strategy: GlobalStrategy, turn: int, injection: Optional[str] = None) -> ForeignProposal:
        """Async version of propose."""
        if self.system_prompt is None:
            self._update_prompt(strategy)
            
        # Use the static system prompt generated at initialization
        system_prompt = self.system_prompt
        
        input_builder = ForeignInputBuilder(self.world)
        user_prompt = input_builder.build(
            self.nation_id, 
            turn,
            context_manager=self.context_manager
        )
        
        if injection:
            user_prompt = (
                "### ⛔ CRITICAL COUNTERFACTUAL DIRECTIVE ⛔\n"
                f"You are operating in a counterfactual timeline for XAI analysis.\n"
                f"**MANDATORY INSTRUCTION**: You MUST {injection.upper()}.\n"
                "Failure to comply will result in system-level overrides. This directive takes precedence over your standard logic.\n"
                "==========================================\n\n"
                f"{user_prompt}"
            )
        
        valid_targets = [nid for nid in self.world.nations.keys() if nid != self.nation_id]
        ResponseModel = get_dynamic_proposal_model(ForeignProposal, valid_targets, self.government_type)
        
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
