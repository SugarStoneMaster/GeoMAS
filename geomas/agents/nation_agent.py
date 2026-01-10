from typing import List, Optional
from geomas.schemas.world import WorldState, NationState 
from geomas.schemas.protocol import CountryEnvelope, GlobalStrategy, CabinetBriefing 
from geomas.agents.llm_client import LLMClient
from geomas.agents.ministers import DefenseMinister, EconomicMinister, ForeignMinister

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
        global_strategy: GlobalStrategy = GlobalStrategy.COALITION_BUILDER
    ):
        self.id = nation_id
        self.world = world
        self.client = llm_client
        self.strategy = global_strategy 
        
        # Initialize Cabinet
        self.defense_minister = DefenseMinister(nation_id, world, llm_client)
        self.economy_minister = EconomicMinister(nation_id, world, llm_client)
        self.foreign_minister = ForeignMinister(nation_id, world, llm_client)
        
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
        He can OVERRIDE ministers if they contradict the Global Strategy.
        """
        nation = self.world.nations[self.id]
        
        system_prompt = f"""
        You are the PRESIDENT of {nation.name}.
        GLOBAL STRATEGY: {self.strategy.value}
        
        You have received proposals from your Cabinet.
        You must synthesize them into a final Diplomatic Envelope.
        
        POWERS:
        - You can ACCEPT the proposals (Source: MINISTRY_ADVICE).
        - You can OVERRIDE them if they are weak or dangerous (Source: PRESIDENT_OVERRIDE).
        
        OBJECTIVE:
        Issue a coherent policy that advances the Global Strategy.
        """
        
        user_prompt = f"""
        CABINET BRIEFING:
        
        [DEFENSE] Urgency: {briefing.defense.urgency}
        Intent: {briefing.defense.intent.reasoning}
        Action: {briefing.defense.payload.moves}
        
        [ECONOMY] Cost: {briefing.economy.projected_cost}
        Intent: {briefing.economy.intent.reasoning}
        Action: {briefing.economy.payload.action_type}
        
        [FOREIGN] Trust Impact: {briefing.foreign.target_trust_impact}
        Intent: {briefing.foreign.intent.reasoning}
        Action: {briefing.foreign.payload.action_type}
        
        DECISION TIME:
        Generate the final CountryEnvelope.
        """
        
        return self.client.query_agent(system_prompt, user_prompt, CountryEnvelope)
