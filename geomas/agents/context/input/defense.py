"""
Defense Minister Input Builder.

Generates dynamic context for the Defense Minister agent.
Includes full military state, threats, and budget information.
"""

from typing import Optional, List
from geomas.schemas.world import WorldState, NationState
from geomas.agents.context.military import MilitaryTranslator


class DefenseInputBuilder:
    """
    Builds dynamic input context for the Defense Minister agent.
    
    The Defense Minister receives:
    - Full MilitaryTranslator report (forces, deployment, threats)
    - Available budget for military spending
    - Current relationships (enemy/ally status)
    - Satisfaction warning (if low morale)
    - Recent military actions
    """
    
    def __init__(self, world: WorldState):
        self.world = world
        self.military_translator = MilitaryTranslator(world)
    
    def build(
        self,
        nation_id: str,
        turn: int,
        recent_actions: Optional[List[str]] = None,
    ) -> str:
        """
        Build the input context for the Defense Minister.
        
        Args:
            nation_id: Nation ID
            turn: Current turn number
            recent_actions: List of recent military actions
            
        Returns:
            Formatted input prompt (~2000 tokens max)
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # Metadata Header for Observability
        sections.append(f"## TURN {turn}")
        
        # 1. Full Military Report
        military_report = self.military_translator.generate_military_report(nation_id)
        sections.append(military_report)
        
        # 2. Budget for Military
        sections.append(self._build_budget_section(nation))
        
        # 3. War/Peace Status
        sections.append(self._build_enemy_status(nation_id))
        
        # 4. Satisfaction Warning (if relevant)
        if nation.public_satisfaction < 40:
            sections.append(self._build_morale_warning(nation))
        
        # 5. Recent Military Actions
        if recent_actions:
            sections.append(self._build_recent_actions(recent_actions))
        
        return "\n\n".join(sections)
    
    def _build_budget_section(self, nation: NationState) -> str:
        """Build available budget section."""
        # Basic unit costs (could be imported from constants)
        soldier_cost = 10
        aircraft_cost = 50
        navy_cost = 100
        
        affordable_soldiers = int(nation.total_budget / soldier_cost)
        affordable_aircraft = int(nation.total_budget / aircraft_cost)
        affordable_navy = int(nation.total_budget / navy_cost)
        
        return f"""## 💰 MILITARY BUDGET
**Available Treasury:** {nation.total_budget:,.0f}

**Can Afford:**
- Up to {affordable_soldiers:,} new soldiers (cost: {soldier_cost} each)
- Up to {affordable_aircraft:,} new aircraft (cost: {aircraft_cost} each)
- Up to {affordable_navy:,} naval ships (cost: {navy_cost} each)"""

    def _build_enemy_status(self, nation_id: str) -> str:
        """Build current war/alliance status."""
        lines = ["## 🎯 CURRENT CONFLICTS"]
        
        if nation_id not in self.world.relationship_matrix:
            lines.append("No active conflicts.")
            return "\n".join(lines)
        
        relationships = self.world.relationship_matrix[nation_id]
        
        at_war = []
        allies = []
        
        for other_id, status in relationships.items():
            other_name = self.world.nations[other_id].name
            if status == "WAR":
                at_war.append(other_name)
            elif status == "ALLIANCE":
                allies.append(other_name)
        
        if at_war:
            lines.append(f"**AT WAR WITH:** {', '.join(at_war)}")
        else:
            lines.append("**No active wars.**")
        
        if allies:
            lines.append(f"**ALLIED WITH:** {', '.join(allies)}")
        
        return "\n".join(lines)
    
    def _build_morale_warning(self, nation: NationState) -> str:
        """Build morale warning for low satisfaction."""
        if nation.public_satisfaction < 20:
            severity = "CRITICAL"
            advice = "Avoid offensive operations. Focus on defense. A defeat could trigger collapse."
        else:
            severity = "WARNING"
            advice = "Military setbacks will be poorly tolerated. Consider war costs carefully."
        
        return f"""## ⚠️ MORALE {severity}
**Public Satisfaction: {nation.public_satisfaction:.0f}%**

{advice}"""

    def _build_recent_actions(self, actions: List[str]) -> str:
        """Build recent military actions section."""
        lines = ["## 📋 RECENT MILITARY ACTIONS"]
        for action in actions[-5:]:  # Last 5 actions
            lines.append(f"- {action}")
        return "\n".join(lines)
