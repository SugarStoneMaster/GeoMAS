"""
NationAgent.

The Cognitive Entity representing a Nation.
Orchestrates the Cabinet (Ministers) and the President.
"""
from typing import List, Optional
from geomas.schemas.world import WorldState, NationState 
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, CabinetBriefing, 
    PresidentialDecree, DecreeAction,
    DefenseProposal, EconomicProposal, ForeignProposal
)
from geomas.actions.common import DecisionSource
from geomas.actions.defense import DefensePayload
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload
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
        2. President Decides (Veto or Approve)
        """
        
        # 1. CABINET PHASE
        def_prop = self.defense_minister.propose(self.strategy)
        eco_prop = self.economy_minister.propose(self.strategy)
        for_prop = self.foreign_minister.propose(self.strategy)
        
        briefing = CabinetBriefing(
            defense=def_prop,
            economy=eco_prop,
            foreign=for_prop
        )

        # 2. PRESIDENTIAL PHASE
        decree = self._presidential_decision(turn, briefing)
        
        # 3. ENFORCE DECREE (Construct Envelope)
        envelope = self._construct_envelope_from_decree(turn, decree, briefing)
        
        # 4. MEMORIZE
        self.memory.append(f"Turn {turn}: {envelope.public_statement}")
        
        return envelope

    def _presidential_decision(self, turn: int, briefing: CabinetBriefing) -> PresidentialDecree:
        """
        The President reviews the briefing and issues a Decree.
        """
        nation = self.world.nations[self.id]
        
        # Generate system prompt
        system_prompt = PresidentSystemPrompt.generate(
            nation_name=nation.name,
            strategy=self.strategy,
            cultural_traits=getattr(nation, 'cultural_traits', None)
        )
        
        # Build input context
        input_builder = PresidentInputBuilder(self.world)
        
        # Get detailed minister summaries
        defense_summary = self._summarize_defense(briefing.defense)
        economy_summary = self._summarize_economy(briefing.economy)
        foreign_summary = self._summarize_foreign(briefing.foreign)
        
        user_prompt = input_builder.build(
            nation_id=self.id,
            defense_summary=defense_summary,
            economy_summary=economy_summary,
            foreign_summary=foreign_summary
        )
        
        # Add memory context
        if self.context_manager:
            relationships = self.context_manager.get_relationships_for(self.id)
            events = self.context_manager.get_events_for(self.id, max_events=10)
            actions = self.context_manager.get_actions_for(self.id, max_actions=10)
            
            if relationships:
                user_prompt += "\n\n== RELATIONSHIP HISTORY ==\n" + "\n".join(f"- {r}" for r in relationships[:5])
            if events:
                user_prompt += "\n\n== RECENT WORLD EVENTS ==\n" + "\n".join(events[:5])
            if actions:
                user_prompt += "\n\n== YOUR RECENT DECISIONS ==\n" + "\n".join(actions[:5])
        
        # Call LLM expecting PresidentialDecree
        return self.client.query_agent(system_prompt, user_prompt, PresidentialDecree)

    def _construct_envelope_from_decree(self, turn: int, decree: PresidentialDecree, briefing: CabinetBriefing) -> CountryEnvelope:
        """Apply Veto/Approve logic to build final envelope."""
        
        # Defense
        if decree.defense.action == DecreeAction.APPROVE:
            def_payload = briefing.defense.payload
            if hasattr(def_payload, 'source'): def_payload.source = DecisionSource.MINISTRY_ADVICE
        else: # VETO -> IDLE action
            def_payload = DefensePayload(source=DecisionSource.PRESIDENT_VETO, moves=[])

        # Economy
        if decree.economy.action == DecreeAction.APPROVE:
            eco_payload = briefing.economy.payload
            if hasattr(eco_payload, 'source'): eco_payload.source = DecisionSource.MINISTRY_ADVICE
        else: # VETO -> No action
            eco_payload = EconomicPayload(source=DecisionSource.PRESIDENT_VETO, action_type=None)

        # Foreign
        if decree.foreign.action == DecreeAction.APPROVE:
            for_payload = briefing.foreign.payload
            if hasattr(for_payload, 'source'): for_payload.source = DecisionSource.MINISTRY_ADVICE
        else: # VETO -> No action
            for_payload = ForeignPayload(source=DecisionSource.PRESIDENT_VETO, action_type=None)

        return CountryEnvelope(
            turn=turn,
            sender_id=self.id,
            global_strategy=self.strategy, # Strategy is fixed, decree metadata is for reference
            public_statement=decree.public_statement,
            
            defense_payload=def_payload,
            defense_public_intent=decree.defense_public_intent,
            defense_private_intent=decree.defense_private_intent,
            defense_private_reasoning=decree.defense_private_reasoning,
            
            economic_payload=eco_payload,
            economic_public_intent=decree.economic_public_intent,
            economic_private_intent=decree.economic_private_intent,
            economic_private_reasoning=decree.economic_private_reasoning,
            
            foreign_payload=for_payload,
            foreign_public_intent=decree.foreign_public_intent,
            foreign_private_intent=decree.foreign_private_intent,
            foreign_private_reasoning=decree.foreign_private_reasoning
        )

    def _summarize_defense(self, proposal: DefenseProposal) -> str:
        """Format defense proposal for President."""
        intent = proposal.intent
        payload = proposal.payload
        summary = f"**Intent:** {intent.type.value} - {intent.reasoning}\n**Urgency:** {proposal.urgency}/10\n**Actions:**"
        
        # Count action types from the generic 'moves' list
        move_count = 0
        recruit_count = 0
        nuke_count = 0
        
        # Note: DefensePayload uses 'moves' list for ALL actions (Waterfall Logic)
        if hasattr(payload, 'moves') and payload.moves:
            for action in payload.moves:
                # Check action type string loosely to handle Enum or str
                a_type = str(action.action_type).upper()
                if "MOVE" in a_type:
                    move_count += 1
                elif "CREATE" in a_type or "RECRUIT" in a_type:
                    recruit_count += 1
                elif "NUKE" in a_type or "NUCLEAR" in a_type:
                    nuke_count += 1
        
        actions = []
        if move_count > 0: actions.append(f"Move/Attack with {move_count} units")
        if recruit_count > 0: actions.append(f"Recruit {recruit_count} units")
        if nuke_count > 0: actions.append(f"LAUNCH {nuke_count} NUKES")
        
        if not actions: return summary + " None"
        return summary + " " + ", ".join(actions)

    def _summarize_economy(self, proposal: EconomicProposal) -> str:
        """Format economic proposal for President."""
        intent = proposal.intent
        payload = proposal.payload
        summary = f"**Intent:** {intent.type.value} - {intent.reasoning}\n**Cost:** {proposal.projected_cost:.1f}\n**Action:**"
        
        if payload.action_type:
            details = str(payload.parameters) if payload.parameters else ""
            return f"{summary} {payload.action_type.value} {details}"
        return f"{summary} None"

    def _summarize_foreign(self, proposal: ForeignProposal) -> str:
        """Format foreign proposal for President."""
        intent = proposal.intent
        payload = proposal.payload
        summary = f"**Intent:** {intent.type.value} - {intent.reasoning}\n**Trust Impact:** {proposal.target_trust_impact:+.0f}\n**Action:**"
        
        if payload.action_type:
            target = f" (Target: {payload.target_nation_id})" if payload.target_nation_id else ""
            details = str(payload.parameters) if payload.parameters else ""
            return f"{summary} {payload.action_type.value}{target} {details}"
        return f"{summary} None"
