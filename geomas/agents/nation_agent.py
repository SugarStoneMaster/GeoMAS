"""
NationAgent.

The Cognitive Entity representing a Nation.
Orchestrates the Cabinet (Ministers) and the President.
"""
from typing import List, Optional
from geomas.schemas.world import WorldState, NationState 
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy, CabinetBriefing
from geomas.agents.llm_client import LLMClient
from geomas.agents.ministers import DefenseMinister, EconomicMinister, ForeignMinister
from geomas.agents.context.system import PresidentSystemPrompt
from geomas.agents.context.input import PresidentInputBuilder
from geomas.agents.context.memory import ContextManager


class NationAgent:
    """
    The Cognitive Entity representing a Nation.
    Orchestrates the Cabinet (Ministers) and the President.
    """

    def __init__(
        self, 
        nation_id: str, 
        world: WorldState, 
        llm_client: LLMClient,
        global_strategy: GlobalStrategy = GlobalStrategy.COALITION_BUILDER,
        context_manager: Optional[ContextManager] = None
    ):
        self.id = nation_id
        self.world = world
        self.client = llm_client
        self.strategy = global_strategy 
        self.context_manager = context_manager
        
        # Initialize Cabinet (pass context_manager for memory access)
        self.defense_minister = DefenseMinister(nation_id, world, llm_client, context_manager)
        self.economy_minister = EconomicMinister(nation_id, world, llm_client, context_manager)
        self.foreign_minister = ForeignMinister(nation_id, world, llm_client, context_manager)
        
        self.memory: List[str] = [] 

    def act(self, turn: int) -> CountryEnvelope:
        """
        Main cognitive loop:
        1. Ministers Propose
        2. President Decides (Override or Accept)
        """
        
        # 1. CABINET PHASE (Parallelizable)
        def_prop = self.defense_minister.propose(self.strategy)
        eco_prop = self.economy_minister.propose(self.strategy)
        for_prop = self.foreign_minister.propose(self.strategy)
        
        briefing = CabinetBriefing(
            defense=def_prop,
            economy=eco_prop,
            foreign=for_prop
        )

        # 2. PRESIDENTIAL PHASE
        envelope = self._presidential_decision(turn, briefing)
        
        # FIX: Enforce correct sender_id and turn (LLM might hallucinate)
        envelope.sender_id = self.id
        envelope.turn = turn
        
        # 3. MEMORIZE
        self.memory.append(f"Turn {turn}: {envelope.public_statement}")
        
        return envelope

    def _presidential_decision(self, turn: int, briefing: CabinetBriefing) -> CountryEnvelope:
        """
        The President reviews the briefing and issues the final envelope.
        Uses new prompt architecture with ContextManager memory.
        """
        nation = self.world.nations[self.id]
        
        # Get cultural traits from nation
        cultural_traits = getattr(nation, 'cultural_traits', None)
        
        # Generate system prompt using new architecture
        system_prompt = PresidentSystemPrompt.generate(
            nation_name=nation.name,
            strategy=self.strategy,
            cultural_traits=cultural_traits
        )
        
        # Build input context using new architecture
        input_builder = PresidentInputBuilder(self.world)
        
        # Get minister summaries for President
        defense_summary = self._summarize_proposal(briefing.defense, "defense")
        economy_summary = self._summarize_proposal(briefing.economy, "economy")
        foreign_summary = self._summarize_proposal(briefing.foreign, "foreign")
        
        user_prompt = input_builder.build(
            nation_id=self.id,
            defense_summary=defense_summary,
            economy_summary=economy_summary,
            foreign_summary=foreign_summary
        )
        
        # Add memory context if ContextManager is available
        if self.context_manager:
            relationships = self.context_manager.get_relationships_for(self.id)
            events = self.context_manager.get_events_for(self.id, max_events=10)
            actions = self.context_manager.get_actions_for(self.id, max_actions=10)
            
            if relationships:
                user_prompt += "\n\n== RELATIONSHIP HISTORY ==\n"
                user_prompt += "\n".join(f"- {r}" for r in relationships[:5])
            
            if events:
                user_prompt += "\n\n== RECENT WORLD EVENTS ==\n"
                user_prompt += "\n".join(events[:5])
            
            if actions:
                user_prompt += "\n\n== YOUR RECENT DECISIONS ==\n"
                user_prompt += "\n".join(actions[:5])
        
        return self.client.query_agent(system_prompt, user_prompt, CountryEnvelope)
    
    def _summarize_proposal(self, proposal, domain: str) -> str:
        """Create a brief summary of a minister's proposal for the President."""
        if proposal is None:
            return f"No {domain} proposal."
        
        intent = getattr(proposal, 'intent', None)
        reasoning = intent.reasoning if intent and hasattr(intent, 'reasoning') else "No reasoning"
        
        if domain == "defense":
            urgency = getattr(proposal, 'urgency', "NORMAL")
            return f"Urgency: {urgency}. {reasoning[:100]}"
        elif domain == "economy":
            cost = getattr(proposal, 'projected_cost', 0)
            return f"Cost: {cost}. {reasoning[:100]}"
        elif domain == "foreign":
            impact = getattr(proposal, 'target_trust_impact', 0)
            return f"Trust Impact: {impact:+.0f}. {reasoning[:100]}"
        
        return reasoning[:150]
