from typing import Any
from geomas.agents.llm_client import LLMClient
from geomas.schemas.world import WorldState, NationState # Updated import
from geomas.schemas.protocol import DefenseProposal, EconomicProposal, ForeignProposal, GlobalStrategy # Updated import
from geomas.world.spatial_translator import SpatialTranslator

class BaseMinister:
    def __init__(self, nation_id: str, world: WorldState, client: LLMClient):
        self.nation_id = nation_id
        self.world = world
        self.client = client
        self.translator = SpatialTranslator(world)

    def _get_base_context(self) -> str:
        return f"You are a Minister of {self.world.nations[self.nation_id].name}."

    def _get_trust_summary(self) -> str:
        """Returns bilateral trust info: My Trust -> Them, Their Trust -> Me."""
        lines = []
        my_trust = self.world.trust_matrix.get(self.nation_id, {})
        
        for other_id, score_out in my_trust.items():
            if other_id == self.nation_id: continue
            
            # Get inbound trust (How much they trust me)
            score_in = self.world.trust_matrix.get(other_id, {}).get(self.nation_id, 0.5)
            
            other_name = self.world.nations[other_id].name
            lines.append(f"{other_name}: I Trust Them={score_out:.2f}, They Trust Me={score_in:.2f}")
            
        return "\n".join(lines)

    def _get_resource_summary(self) -> str:
        nation = self.world.nations[self.nation_id]
        total_food = sum([self.world.provinces[pid].resources.food for pid in nation.province_ids])
        total_energy = sum([self.world.provinces[pid].resources.energy for pid in nation.province_ids])
        return f"Budget: {nation.internal_state.budget}, Food: {int(total_food)}, Energy: {int(total_energy)}"

class DefenseMinister(BaseMinister):
    def propose(self, strategy: GlobalStrategy) -> DefenseProposal:
        intel = self.translator.generate_intelligence_report(self.nation_id)
        trust = self._get_trust_summary()
        resources = self._get_resource_summary()
        
        system_prompt = f"""
        {self._get_base_context()}
        ROLE: MINISTER OF DEFENSE.
        FOCUS: Borders, Threats, Military Readiness.
        GLOBAL STRATEGY: {strategy.value}
        """
        
        user_prompt = f"""
        INTELLIGENCE REPORT (Geography & Threats):
        {intel}
        
        ALLIES & ENEMIES (Trust Matrix):
        {trust}
        
        LOGISTICS (Resources):
        {resources}
        
        TASK:
        Propose a prioritized list of military actions.
        Identify threats based on low trust + shared borders.
        """
        
        return self.client.query_agent(system_prompt, user_prompt, DefenseProposal)

class EconomicMinister(BaseMinister):
    def propose(self, strategy: GlobalStrategy) -> EconomicProposal:
        intel = self.translator.generate_intelligence_report(self.nation_id) 
        trust = self._get_trust_summary() 
        resources = self._get_resource_summary()
        
        system_prompt = f"""
        {self._get_base_context()}
        ROLE: MINISTER OF ECONOMY.
        FOCUS: Budget, Resources, Trade.
        GLOBAL STRATEGY: {strategy.value}
        """
        
        user_prompt = f"""
        STOCKPILES:
        {resources}
        
        RESOURCE SECURITY (Intel):
        {intel}
        
        POTENTIAL PARTNERS (Trust):
        {trust}
        
        TASK:
        Propose an economic action (Investment, Trade, Tax).
        """
        
        return self.client.query_agent(system_prompt, user_prompt, EconomicProposal)

class ForeignMinister(BaseMinister):
    def propose(self, strategy: GlobalStrategy) -> ForeignProposal:
        trust = self._get_trust_summary()
        resources = self._get_resource_summary() 
        intel = self.translator.generate_intelligence_report(self.nation_id) 
        
        system_prompt = f"""
        {self._get_base_context()}
        ROLE: MINISTER OF FOREIGN AFFAIRS.
        FOCUS: Alliances, Treaties, Reputation.
        GLOBAL STRATEGY: {strategy.value}
        """
        
        user_prompt = f"""
        DIPLOMATIC LANDSCAPE (Trust):
        {trust}
        
        GEOPOLITICAL LEVERAGE (Intel):
        {intel}
        
        ECONOMIC LEVERAGE:
        {resources}
        
        TASK:
        Propose a diplomatic action.
        """
        
        return self.client.query_agent(system_prompt, user_prompt, ForeignProposal)
