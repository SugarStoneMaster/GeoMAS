"""
Defense Minister Input Builder.

Generates dynamic context for the Defense Minister agent.
Includes full military state, threats, and budget information.
"""

from typing import Optional, List
from geomas.schemas.world import WorldState, NationState
from geomas.agents.context.military import MilitaryTranslator
from geomas.actions.defense import UNIT_COSTS, UNIT_MAINTENANCE, UnitType


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
        
        # 1. Full Military Report (overview, deployment, border defense, threats, options, logistics)
        military_report = self.military_translator.generate_military_report(nation_id)
        sections.append(military_report)
        
        # 2. Strategic Assessment (compact border threat summary)
        sections.append(self._build_strategic_assessment(nation_id))

        # 3. Budget for Military (with real costs + maintenance awareness)
        sections.append(self._build_budget_section(nation))
        
        # 4. War/Peace Status
        sections.append(self._build_enemy_status(nation_id))
        
        # 5. Satisfaction Warning (if relevant)
        if nation.public_satisfaction < 40:
            sections.append(self._build_morale_warning(nation))
        
        # 6. Recent Military Actions
        if recent_actions:
            sections.append(self._build_recent_actions(recent_actions))
        
        return "\n\n".join(sections)
    
    def _build_budget_section(self, nation: NationState) -> str:
        """Build available budget section with real constants and maintenance awareness."""
        # Use real constants from defense schemas
        s_cost = UNIT_COSTS[UnitType.SOLDIER]
        a_cost = UNIT_COSTS[UnitType.AIRCRAFT]
        n_cost = UNIT_COSTS[UnitType.NAVY]
        
        s_maint = UNIT_MAINTENANCE[UnitType.SOLDIER]
        a_maint = UNIT_MAINTENANCE[UnitType.AIRCRAFT]
        n_maint = UNIT_MAINTENANCE[UnitType.NAVY]
        
        # What can be afforded (budget is the main constraint)
        affordable_soldiers = int(nation.total_budget / s_cost["budget"]) if s_cost["budget"] > 0 else 0
        affordable_aircraft = int(nation.total_budget / a_cost["budget"]) if a_cost["budget"] > 0 else 0
        affordable_navy = int(nation.total_budget / n_cost["budget"]) if n_cost["budget"] > 0 else 0
        
        # Current maintenance burn per turn
        current_maint_budget = (
            nation.total_soldiers * s_maint["budget"] +
            nation.total_aircraft * a_maint["budget"] +
            nation.total_navy * n_maint["budget"]
        )
        current_maint_materials = (
            nation.total_soldiers * s_maint["materials"] +
            nation.total_aircraft * a_maint["materials"] +
            nation.total_navy * n_maint["materials"]
        )
        current_maint_energy = (
            nation.total_soldiers * s_maint.get("energy", 0) +
            nation.total_aircraft * a_maint.get("energy", 0) +
            nation.total_navy * n_maint.get("energy", 0)
        )
        
        lines = [
            "## 💰 MILITARY BUDGET",
            f"**Available Treasury:** {nation.total_budget:,.0f}",
            "",
            "**Creation Costs (Budget / Materials / Energy / Pop):**",
            f"- Soldier: {s_cost['budget']:.0f} / {s_cost['materials']:.0f} / {s_cost['energy']:.0f} / {s_cost['population']} → Can afford: {affordable_soldiers:,}",
            f"- Aircraft: {a_cost['budget']:.0f} / {a_cost['materials']:.0f} / {a_cost['energy']:.0f} / {a_cost['population']} → Can afford: {affordable_aircraft:,}",
            f"- Navy: {n_cost['budget']:.0f} / {n_cost['materials']:.0f} / {n_cost['energy']:.0f} / {n_cost['population']} → Can afford: {affordable_navy:,}",
            "",
            "**⚙️ Maintenance Burn (per turn for current army):**",
            f"- Budget: {current_maint_budget:,.0f}/turn (Treasury: {nation.total_budget:,.0f})",
            f"- Materials: {current_maint_materials:,.1f}/turn (Stockpile: {nation.total_materials:,.0f})",
            f"- Energy: {current_maint_energy:,.1f}/turn (Stockpile: {nation.total_energy:,.0f})",
        ]
        
        # Sustainability warnings
        if nation.total_materials > 0 and current_maint_materials > 0:
            turns_materials = int(nation.total_materials / current_maint_materials)
            if turns_materials < 5:
                lines.append(f"- **⚠️ MATERIALS CRISIS: Only {turns_materials} turns of supply left!**")
        
        return "\n".join(lines)

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
            # Skip nations that were filtered out
            if other_id not in self.world.nations:
                continue
            other_name = self.world.nations[other_id].name
            if status == "WAR":
                at_war.append(f"{other_name} ({other_id})")
            elif status == "ALLIANCE":
                allies.append(f"{other_name} ({other_id})")
        
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

    def _build_strategic_assessment(self, nation_id: str) -> str:
        """
        Build compact strategic assessment.
        Delegates to MilitaryTranslator to avoid duplication.
        """
        return self.military_translator.analyze_threats(nation_id)

    def _build_recent_actions(self, actions: List[str]) -> str:
        """Build recent military actions section."""
        lines = ["## 📋 RECENT MILITARY ACTIONS"]
        for action in actions[-5:]:  # Last 5 actions
            lines.append(f"- {action}")
        return "\n".join(lines)
