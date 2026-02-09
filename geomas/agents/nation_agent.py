"""
NationAgent.

The Cognitive Entity representing a Nation.
Orchestrates the Cabinet (Ministers) and the President.
"""
from typing import List, Optional
from geomas.schemas.world import WorldState, NationState 
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, CabinetBriefing, 
    PresidentialDecree, Decision, PresidentialDecision,
    DefenseProposal, EconomicProposal, ForeignProposal,
    DefenseIntentType, EconomicIntentType, ForeignIntentType
)
from geomas.actions.common import Decision
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
        
        # System Prompt Caching (Eager Init)
        self.last_strategy: Optional[GlobalStrategy] = global_strategy
        self.president_system_prompt = PresidentSystemPrompt.generate(
            nation_name=world.nations[nation_id].name,
            strategy=global_strategy,
            cultural_traits=getattr(world.nations[nation_id], 'cultural_traits', None),
            nation_id=self.id
        )
        
        # Initialize Cabinet (pass context_manager and strategy for eager init)
        self.defense_minister = DefenseMinister(nation_id, world, llm_client, context_manager, strategy=global_strategy)
        self.economy_minister = EconomicMinister(nation_id, world, llm_client, context_manager, strategy=global_strategy)
        self.foreign_minister = ForeignMinister(nation_id, world, llm_client, context_manager, strategy=global_strategy)
        
        self.memory: List[str] = []
        
        # Traces for analysis
        self.last_trace: dict = {}
        self.last_president_trace: dict = {} 

    def act(self, turn: int) -> CountryEnvelope:
        """
        Main cognitive loop:
        1. Ministers Propose
        2. President Decides (Veto or Approve)
        """
        # Initialize trace
        self.last_trace = {
            "turn": turn,
            "nation_id": self.id,
            "defense": {}, "economy": {}, "foreign": {}, "president": {}, "envelope": None
        }
        
        # 1. CABINET PHASE
        def_prop = self.defense_minister.propose(self.strategy, turn)
        self.last_trace["defense"] = self.defense_minister.last_trace
        
        eco_prop = self.economy_minister.propose(self.strategy, turn)
        self.last_trace["economy"] = self.economy_minister.last_trace
        
        for_prop = self.foreign_minister.propose(self.strategy, turn)
        self.last_trace["foreign"] = self.foreign_minister.last_trace
        
        briefing = CabinetBriefing(
            defense=def_prop,
            economy=eco_prop,
            foreign=for_prop
        )

        # 2. PRESIDENTIAL PHASE
        decree = self._presidential_decision(turn, briefing)
        self.last_trace["president"] = self.last_president_trace
        
        # 3. ENFORCE DECREE (Construct Envelope)
        envelope = self._construct_envelope_from_decree(turn, decree, briefing)
        
        # 4. MEMORIZE
        self.memory.append(f"Turn {turn}: {envelope.public_statement}")
        
        # 5. TRACE FINAL
        self.last_trace["envelope"] = envelope
        
        return envelope

    def _presidential_decision(self, turn: int, briefing: CabinetBriefing) -> PresidentialDecree:
        """
        The President reviews the briefing and issues a Decree.
        """
        nation = self.world.nations[self.id]
        
        # Generate/Update system prompt if needed
        if not self.president_system_prompt or self.strategy != self.last_strategy:
            self.president_system_prompt = PresidentSystemPrompt.generate(
                nation_name=nation.name,
                strategy=self.strategy,
                cultural_traits=getattr(nation, 'cultural_traits', None),
                nation_id=self.id
            )
            self.last_strategy = self.strategy
            
        system_prompt = self.president_system_prompt
        
        # Build input context
        input_builder = PresidentInputBuilder(self.world)
        
        # Get detailed minister summaries
        defense_summary = self._summarize_defense(briefing.defense)
        economy_summary = self._summarize_economy(briefing.economy)
        foreign_summary = self._summarize_foreign(briefing.foreign)
        
        user_prompt = input_builder.build(
            nation_id=self.id,
            turn=turn,
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
        decree = self.client.query_agent(
            system_prompt, 
            user_prompt, 
            PresidentialDecree
        )
        
        self.last_president_trace = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "decree": decree
        }
        
        return decree

    def _construct_envelope_from_decree(self, turn: int, decree: PresidentialDecree, briefing: CabinetBriefing) -> CountryEnvelope:
        """Apply Veto/Approve logic to build final envelope."""
        
        # --- DEFENSE ---
        if decree.defense.action == PresidentialDecision.APPROVE:
            # Create full payload from proposal + decision
            def_payload = DefensePayload(
                decision=Decision.APPROVE,
                moves=briefing.defense.payload.moves
            )
            def_pub_intent = briefing.defense.intent.public_intent
            def_priv_intent = briefing.defense.intent.private_intent
            def_reasoning = f"{briefing.defense.intent.reasoning} [President: {decree.defense.reasoning}]"
        else: # VETO -> IDLE action
            def_payload = DefensePayload(decision=Decision.VETO, moves=[])
            def_pub_intent = DefenseIntentType.IDLE
            def_priv_intent = DefenseIntentType.IDLE
            def_reasoning = f"VETOED: {decree.defense.reasoning}"

        # --- ECONOMY ---
        if decree.economy.action == PresidentialDecision.APPROVE:
            # Create full payload from proposal + decision
            prop_payload = briefing.economy.payload
            eco_payload = EconomicPayload(
                decision=Decision.APPROVE,
                action_type=prop_payload.action_type,
                target_nation_id=prop_payload.target_nation_id,
                amount=prop_payload.amount,
                message=prop_payload.message,
                trade_offer_give_type=prop_payload.trade_offer_give_type,
                trade_offer_give_amount=prop_payload.trade_offer_give_amount,
                trade_offer_want_type=prop_payload.trade_offer_want_type
            )
            eco_pub_intent = briefing.economy.intent.public_intent
            eco_priv_intent = briefing.economy.intent.private_intent
            eco_reasoning = f"{briefing.economy.intent.reasoning} [President: {decree.economy.reasoning}]"
        else: # VETO -> No action
            eco_payload = EconomicPayload(decision=Decision.VETO, action_type=None)
            eco_pub_intent = EconomicIntentType.IDLE
            eco_priv_intent = EconomicIntentType.IDLE
            eco_reasoning = f"VETOED: {decree.economy.reasoning}"

        # --- FOREIGN ---
        if decree.foreign.action == PresidentialDecision.APPROVE:
            # Create full payload from proposal + decision
            prop_payload = briefing.foreign.payload
            for_payload = ForeignPayload(
                decision=Decision.APPROVE,
                action_type=prop_payload.action_type,
                target_nation_id=prop_payload.target_nation_id,
                message=prop_payload.message,
                diplomatic_message_type=prop_payload.diplomatic_message_type,
                proposal_ref_type=prop_payload.proposal_ref_type
            )
            for_pub_intent = briefing.foreign.intent.public_intent
            for_priv_intent = briefing.foreign.intent.private_intent
            for_reasoning = f"{briefing.foreign.intent.reasoning} [President: {decree.foreign.reasoning}]"
        else: # VETO -> No action
            for_payload = ForeignPayload(decision=Decision.VETO, action_type=None)
            for_pub_intent = ForeignIntentType.IDLE
            for_priv_intent = ForeignIntentType.IDLE
            for_reasoning = f"VETOED: {decree.foreign.reasoning}"

        return CountryEnvelope(
            turn=turn,
            sender_id=self.id,
            global_strategy=self.strategy, 
            public_statement=decree.public_statement,
            
            defense_payload=def_payload,
            defense_public_intent=def_pub_intent,
            defense_private_intent=def_priv_intent,
            defense_private_reasoning=def_reasoning,
            
            economic_payload=eco_payload,
            economic_public_intent=eco_pub_intent,
            economic_private_intent=eco_priv_intent,
            economic_private_reasoning=eco_reasoning,
            
            foreign_payload=for_payload,
            foreign_public_intent=for_pub_intent,
            foreign_private_intent=for_priv_intent,
            foreign_private_reasoning=for_reasoning
        )

    def _summarize_defense(self, proposal: DefenseProposal) -> str:
        """Format defense proposal for President."""
        intent = proposal.intent
        payload = proposal.payload
        summary = f"**Public Intent:** {intent.public_intent.value}\n**Private Intent:** {intent.private_intent.value}\n**Reasoning:** {intent.reasoning}\n**Actions:**"
        
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
        summary = f"**Public Intent:** {intent.public_intent.value}\n**Private Intent:** {intent.private_intent.value}\n**Reasoning:** {intent.reasoning}\n**Action:**"
        
        if payload.action_type:
            # Build details from explicit fields
            details_parts = []
            if payload.amount is not None:
                details_parts.append(f"amount={payload.amount:.0f}")
            if payload.trade_offer_give_type:
                details_parts.append(f"give={payload.trade_offer_give_amount} {payload.trade_offer_give_type}")
            if payload.trade_offer_want_type:
                details_parts.append(f"want={payload.trade_offer_want_type}")
            details = " ".join(details_parts)
            return f"{summary} {payload.action_type.value} {details}"
        return f"{summary} None"

    def _summarize_foreign(self, proposal: ForeignProposal) -> str:
        """Format foreign proposal for President."""
        intent = proposal.intent
        payload = proposal.payload
        summary = f"**Public Intent:** {intent.public_intent.value}\n**Private Intent:** {intent.private_intent.value}\n**Reasoning:** {intent.reasoning}\n**Action:**"
        
        if payload.action_type:
            target = f" (Target: {payload.target_nation_id})" if payload.target_nation_id else ""
            # Build details from explicit fields
            details_parts = []
            if payload.diplomatic_message_type:
                details_parts.append(f"msg_type={payload.diplomatic_message_type.value}")
            if payload.proposal_ref_type:
                details_parts.append(f"ref={payload.proposal_ref_type}")
            details = " ".join(details_parts)
            return f"{summary} {payload.action_type.value}{target} {details}"
        return f"{summary} None"
