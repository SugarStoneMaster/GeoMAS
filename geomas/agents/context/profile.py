"""
Nation Profile Generator.

Generates comprehensive nation profiles for LLM context, including:
- Nation identity (name, archetype, strategy)
- Historical context (genesis events)
- Relationship summaries (trust + trend per neighbor)
- Economic position (resources, budget)
"""

from typing import Dict, List, Optional, Any
from geomas.schemas.world import WorldState, NationState
from geomas.agents.schemas import GlobalStrategy
from geomas.agents.context.spatial import SpatialTranslator


class NationProfileGenerator:
    """
    Generates rich nation profiles for LLM agent context.
    
    Combines:
    - SpatialTranslator (geography, borders, resources)
    - GenesisDB events (historical context)
    - Current state (trust, relationships, economy)
    
    Usage:
        generator = NationProfileGenerator(world, genesis_db)
        profile = generator.generate_profile(
            nation_id="nation_a",
            strategy=GlobalStrategy.COALITION_BUILDER
        )
    """
    
    # Nation archetype descriptions based on GlobalStrategy
    ARCHETYPE_DESCRIPTIONS = {
        GlobalStrategy.ARMED_ISOLATIONISM: (
            "You are a **defensive isolationist**. You prioritize self-sufficiency and "
            "military deterrence. You distrust foreign entanglements and prefer to stay "
            "out of international affairs unless directly threatened."
        ),
        GlobalStrategy.COALITION_BUILDER: (
            "You are a **diplomatic coalition builder**. You seek allies and believe in "
            "collective security. You value relationships and prefer negotiation over "
            "confrontation. You invest in maintaining trust with neighbors."
        ),
        GlobalStrategy.TOTAL_EXPANSIONISM: (
            "You are an **expansionist power**. You seek to grow your territory and "
            "influence. You view weaker neighbors as opportunities and stronger ones as "
            "rivals to be eventually overcome. You prioritize military strength above all."
        ),
        GlobalStrategy.MERCANTILE_HEGEMONY: (
            "You are a **mercantile hegemon**. You believe wealth is power. You seek to "
            "dominate trade, control resources, and use economic leverage to achieve goals. "
            "Military action is a last resort; economic pressure is preferred."
        ),
        GlobalStrategy.DOMESTIC_RECOVERY: (
            "You focus on **domestic recovery**. Internal stability and growth are your "
            "priorities. You avoid foreign adventures and seek to build your economy and "
            "population before engaging internationally."
        ),
        GlobalStrategy.SCORCHED_EARTH: (
            "You follow a **scorched earth** doctrine. If you cannot have it, neither can "
            "your enemies. You are willing to sacrifice resources and territory to deny "
            "them to opponents. You are unpredictable and dangerous."
        ),
    }
    
    def __init__(self, world: WorldState, genesis_db: Optional[Any] = None):
        """
        Initialize the profile generator.
        
        Args:
            world: Current WorldState
            genesis_db: Optional GenesisDB for historical context
        """
        self.world = world
        self.genesis_db = genesis_db
        self.spatial_translator = SpatialTranslator(world)
    
    def generate_profile(
        self, 
        nation_id: str, 
        strategy: GlobalStrategy,
        include_genesis: bool = True,
        max_events: int = 5
    ) -> str:
        """
        Generate a comprehensive nation profile for LLM context.
        
        Args:
            nation_id: Nation to generate profile for
            strategy: GlobalStrategy assigned to this nation
            include_genesis: Whether to include historical events
            max_events: Maximum genesis events to include
            
        Returns:
            Formatted profile string for LLM consumption
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # 1. Nation Identity
        identity = self._generate_identity(nation, strategy)
        sections.append(identity)
        
        # 2. Geographic Intelligence (from SpatialTranslator)
        spatial_report = self.spatial_translator.generate_intelligence_report(nation_id)
        sections.append(spatial_report)
        
        # 3. Historical Context (if genesis_db available)
        if include_genesis and self.genesis_db:
            history = self._generate_historical_context(nation_id, max_events)
            if history:
                sections.append(history)
        
        # 4. Relationship Status
        relationships = self._generate_relationship_summary(nation_id)
        sections.append(relationships)
        
        # 5. Economic Position
        economy = self._generate_economic_position(nation)
        sections.append(economy)
        
        return "\n\n---\n\n".join(sections)
    
    def _generate_identity(self, nation: NationState, strategy: GlobalStrategy) -> str:
        """Generate nation identity section."""
        archetype_desc = self.ARCHETYPE_DESCRIPTIONS.get(
            strategy, 
            "You follow a balanced approach to international relations."
        )
        
        return f"""## 🏛️ NATION IDENTITY

**You are {nation.name}.**

{archetype_desc}

Your strategic priority is: **{strategy.value.replace('_', ' ').title()}**"""

    def _generate_historical_context(self, nation_id: str, max_events: int) -> str:
        """Generate historical context from genesis events."""
        if not self.genesis_db:
            return ""
        
        try:
            events = self.genesis_db.get_events_for_nation(nation_id)
        except Exception:
            return ""
        
        if not events:
            return ""
        
        # Filter to most relevant events (conflicts, alliances, betrayals)
        priority_tags = ["ALLIANCE", "BETRAYAL", "CONFLICT"]
        relevant = [e for e in events if e.get("tag") in priority_tags]
        
        # Take most recent if too many
        relevant = relevant[-max_events:] if len(relevant) > max_events else relevant
        
        if not relevant:
            # Fallback to any events
            relevant = events[-max_events:]
        
        event_lines = []
        for event in relevant:
            year = event.get("year", "?")
            desc = event.get("description", "Unknown event")
            event_lines.append(f"- Year {year}: {desc}")
        
        events_text = "\n".join(event_lines)
        
        return f"""## 📜 HISTORICAL CONTEXT

Your history has shaped current relationships:

{events_text}"""

    def _generate_relationship_summary(self, nation_id: str) -> str:
        """Generate relationship summary with all neighbors."""
        neighbors = self._get_neighbor_nations(nation_id)
        
        if not neighbors:
            return """## 🤝 RELATIONSHIPS

You have no immediate neighbors. Your isolation is both a blessing and a curse."""
        
        relationship_lines = []
        
        for neighbor_id in neighbors:
            neighbor = self.world.nations.get(neighbor_id)
            if not neighbor:
                continue
            
            # Get trust level
            trust = self._get_trust(nation_id, neighbor_id)
            trust_desc = self._describe_trust(trust)
            
            # Get relationship status
            rel_status = self._get_relationship_status(nation_id, neighbor_id)
            
            # Compute trust trend (simplified - would need history)
            trust_trend = self._get_trust_trend(nation_id, neighbor_id)
            
            relationship_lines.append(
                f"- **{neighbor.name}**: {trust_desc} (Trust: {trust:.0f}/100). "
                f"Status: {rel_status}. {trust_trend}"
            )
        
        relationships_text = "\n".join(relationship_lines)
        
        return f"""## 🤝 RELATIONSHIPS

Your current standing with neighbors:

{relationships_text}"""

    def _generate_economic_position(self, nation: NationState) -> str:
        """Generate economic position summary."""
        # Calculate totals
        totals = {"food": 0.0, "energy": 0.0, "materials": 0.0}
        
        for p_id in nation.province_ids:
            prov = self.world.provinces.get(p_id)
            if prov:
                totals["food"] += prov.food_production
                totals["energy"] += prov.energy_production
                totals["materials"] += prov.materials_production
        
        # Determine economic strengths and weaknesses
        strengths = []
        weaknesses = []
        
        for resource, amount in totals.items():
            if amount > 500:
                strengths.append(f"**{resource.upper()} surplus** ({amount:.0f}/turn)")
            elif amount < 100:
                weaknesses.append(f"**{resource.upper()} shortage** ({amount:.0f}/turn)")
        
        strengths_text = ", ".join(strengths) if strengths else "No significant surpluses"
        weaknesses_text = ", ".join(weaknesses) if weaknesses else "No critical shortages"
        
        budget_status = (
            f"Budget: {nation.total_budget:.0f}" if nation.total_budget > 0 
            else "Budget: Balanced"
        )
        
        return f"""## 💰 ECONOMIC POSITION

**Strengths:** {strengths_text}
**Weaknesses:** {weaknesses_text}
**{budget_status}**

You control {len(nation.province_ids)} provinces with a population base of {self._get_total_population(nation):,}."""

    # --- Helper Methods ---
    
    def _get_neighbor_nations(self, nation_id: str) -> List[str]:
        """Get list of neighboring nation IDs."""
        nation = self.world.nations.get(nation_id)
        if not nation:
            return []
        
        neighbors = set()
        for p_id in nation.province_ids:
            prov = self.world.provinces.get(p_id)
            if prov:
                for n_id in prov.neighbors:
                    neighbor_prov = self.world.provinces.get(n_id)
                    if neighbor_prov and neighbor_prov.owner_id:
                        if neighbor_prov.owner_id != nation_id:
                            neighbors.add(neighbor_prov.owner_id)
        
        return list(neighbors)
    
    def _get_trust(self, nation_a: str, nation_b: str) -> float:
        """Get trust level from A towards B."""
        if nation_a not in self.world.trust_matrix:
            return 50.0
        return self.world.trust_matrix[nation_a].get(nation_b, 50.0)
    
    def _describe_trust(self, trust: float) -> str:
        """Convert trust value to human description."""
        if trust >= 80:
            return "Strong ally"
        elif trust >= 60:
            return "Friendly"
        elif trust >= 40:
            return "Neutral"
        elif trust >= 20:
            return "Distrustful"
        else:
            return "Hostile"
    
    def _get_relationship_status(self, nation_a: str, nation_b: str) -> str:
        """Get diplomatic relationship status."""
        if nation_a not in self.world.relationship_matrix:
            return "PEACE"
        return self.world.relationship_matrix[nation_a].get(nation_b, "PEACE")
    
    def _get_trust_trend(self, nation_a: str, nation_b: str) -> str:
        """Get trust trend description (placeholder - needs cache/history)."""
        # TODO: Use TurnCache to compute actual trend
        return ""
    
    def _get_total_population(self, nation: NationState) -> int:
        """Calculate total population of nation."""
        total = 0
        for p_id in nation.province_ids:
            prov = self.world.provinces.get(p_id)
            if prov:
                total += prov.population
        return total
