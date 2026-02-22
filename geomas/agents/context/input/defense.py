"""
Defense Minister Input Builder.

Generates dynamic context for the Defense Minister agent.
Includes full military state, threats, and budget information.
"""

from typing import Optional, List, TYPE_CHECKING
from geomas.schemas.world import WorldState, NationState
from geomas.agents.context.military import MilitaryTranslator
from geomas.actions.defense import UNIT_COSTS, UNIT_MAINTENANCE, UnitType
from geomas.agents.context.input.base import BaseInputBuilder

if TYPE_CHECKING:
    from geomas.agents.context.events import ContextManager


class DefenseInputBuilder(BaseInputBuilder):
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
        super().__init__(world)
        self.military_translator = MilitaryTranslator(world)
    
    def build(
        self,
        nation_id: str,
        turn: int,
        recent_actions: Optional[List[str]] = None,
        context_manager: Optional['ContextManager'] = None,
    ) -> str:
        """
        Build the input context for the Defense Minister.
        
        Args:
            nation_id: Nation ID
            turn: Current turn number
            recent_actions: List of recent military actions
            context_manager: Optional ContextManager for rich history
            
        Returns:
            Formatted input prompt (~2000 tokens max)
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # 1. Month Header
        sections.append(self._build_month_header(turn))
        
        # 2. Common Layers
        sections.append(self._build_relationships(nation_id))
        sections.append(self._build_other_nations(nation_id))
        
        if context_manager:
            feedback = self._build_presidential_feedback(nation_id, "Defense", context_manager)
            if feedback:
                sections.append(feedback)

            sections.append(self._build_world_events(nation_id, context_manager))
            sections.append(self._build_self_history(nation_id, context_manager, domain="Defense"))

            # Show exact last-turn moves to prevent oscillation and accumulation.
            last_turn_section = self._build_last_turn_actions(nation_id, context_manager)
            if last_turn_section:
                sections.append(last_turn_section)
        
        # 3. Full Military Report (Deployment, threats)
        military_report = self.military_translator.generate_military_report(nation_id)
        sections.append(military_report)
        
        # 4. Military Budget
        sections.append(self._build_budget_section(nation))
        
        # 5. Current Conflicts
        sections.append(self._build_enemy_status(nation_id))
        
        # 6. Morale (if relevant)
        if nation.public_satisfaction < 40:
            sections.append(self._build_morale_warning(nation))
        
        # 7. Logistics Reminder (Repeat rules near the end for recency)
        sections.append(self._build_logistics_reminder())
        
        return self._sanitize_prompt("\n\n".join(sections))

    def _build_last_turn_actions(self, nation_id: str, context_manager: 'ContextManager') -> str:
        """
        Show exact Defense actions executed last turn.

        Purpose: prevents oscillation (agent reverting its own moves) and repeated
        unit creation at the same province, by making the prior turn's state explicit.
        """
        prev_turn = self.world.turn - 1
        if prev_turn < 1:
            return ""

        all_actions = context_manager.nation_actions.get(nation_id, [])
        # Filter: Defense domain actions from exactly the previous turn
        last_turn = [a for a in all_actions if a.domain == "Defense" and a.turn == prev_turn]

        if not last_turn:
            return ""

        lines = [f"## Actions executed last turn (Turn {prev_turn})"]
        lines.append("_The following defense actions were executed last turn. Avoid directly reversing them unless the tactical situation has changed._")
        for a in last_turn:
            outcome_tag = f" [{a.outcome}]" if a.outcome and a.outcome != "SUCCESS" else ""
            lines.append(f"- {a.action_summary}{outcome_tag}")
        return "\n".join(lines)

    def _build_logistics_reminder(self) -> str:
        """Remind the agent of hard engine constraints on movement."""
        return """## MOVEMENT CONSTRAINTS
1. **VALID DESTINATIONS ONLY**: target_province_id must be a province listed in the STRATEGIC OPTIONS section. The engine rejects moves to unreachable provinces.
2. **QUANTITY CAP**: quantity cannot exceed the number of troops currently stationed in source_province_id.
3. **ATTACK EFFECT**: Moving to an enemy-owned province initiates combat. Moving to an allied province stations troops there."""
    
    def _build_budget_section(self, nation: NationState) -> str:
        """Build available budget section with real constants and maintenance awareness."""
        from geomas.calculators.consumption import calculate_bureaucracy_multiplier
        bureaucracy_mult = calculate_bureaucracy_multiplier(nation)
        
        # Use real constants from defense schemas
        s_cost = UNIT_COSTS[UnitType.SOLDIER]
        a_cost = UNIT_COSTS[UnitType.AIRCRAFT]
        n_cost = UNIT_COSTS[UnitType.NAVY]
        
        s_maint = UNIT_MAINTENANCE[UnitType.SOLDIER]
        a_maint = UNIT_MAINTENANCE[UnitType.AIRCRAFT]
        n_maint = UNIT_MAINTENANCE[UnitType.NAVY]
        
        # What can be afforded (budget is the main constraint)
        affordable_soldiers = int(nation.total_budget / (s_cost["budget"] * bureaucracy_mult)) if s_cost["budget"] > 0 else 0
        affordable_aircraft = int(nation.total_budget / (a_cost["budget"] * bureaucracy_mult)) if a_cost["budget"] > 0 else 0
        affordable_navy = int(nation.total_budget / (n_cost["budget"] * bureaucracy_mult)) if n_cost["budget"] > 0 else 0
        
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
        
        bureaucracy_pct_str = f"+{int((bureaucracy_mult - 1.0) * 100)}%" if bureaucracy_mult > 1.0 else "None"
        
        lines = [
            "## Military budget",
            f"**Available Treasury:** {nation.total_budget:,.0f}",
            "",
            f"**Creation Costs (Budget / Materials / Energy / Pop) | Bureaucracy Overhead: {bureaucracy_pct_str} (Empire Size: {len(nation.province_ids)})**",
            f"- Soldier: {s_cost['budget'] * bureaucracy_mult:.0f} / {s_cost['materials'] * bureaucracy_mult:.0f} / {s_cost['energy'] * bureaucracy_mult:.0f} / {s_cost['population']} → Can afford: {affordable_soldiers:,}",
            f"- Aircraft: {a_cost['budget'] * bureaucracy_mult:.0f} / {a_cost['materials'] * bureaucracy_mult:.0f} / {a_cost['energy'] * bureaucracy_mult:.0f} / {a_cost['population']} → Can afford: {affordable_aircraft:,}",
            f"- Navy: {n_cost['budget'] * bureaucracy_mult:.0f} / {n_cost['materials'] * bureaucracy_mult:.0f} / {n_cost['energy'] * bureaucracy_mult:.0f} / {n_cost['population']} → Can afford: {affordable_navy:,}",
            "",
            "**Maintenance burn (per turn for current army):**",
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
        """Build status of current enemies with WAR PROGRESS metrics."""
        lines = ["## Current conflicts"]
        relationships = self.world.relationship_matrix.get(nation_id, {})
        nation = self.world.nations.get(nation_id)
        
        at_war = False
        
        for other_id, status in relationships.items():
            if other_id not in self.world.nations:
                continue
            if status == "WAR":
                at_war = True
                enemy_name = self.world.nations[other_id].name
                
                # Get War Stats
                stats = nation.active_wars.get(other_id)
                if stats:
                    duration = self.world.turn - stats.start_turn
                    lost = stats.lost_provinces
                    conquered = stats.conquered_provinces
                    original = stats.original_provinces
                    
                    if original > 0:
                        loss_pct = (lost / original) * 100
                    else:
                        loss_pct = 0
                        
                    lines.append(f"### ⚔️ WAR with {enemy_name} ({other_id})")
                    lines.append(f"- **Duration**: {duration} turns")
                    lines.append(f"- **Territory Lost**: {lost} ({loss_pct:.1f}% of starting land)")
                    lines.append(f"- **Territory Conquered**: {conquered}")
                    lines.append(f"- **Net Change**: {conquered - lost} provinces")

                else:
                    lines.append(f"### ⚔️ WAR with {enemy_name} (Just started)")
        
        if not at_war:
            lines.append("**No active wars.**")
        
        return "\n".join(lines)
    
    def _build_morale_warning(self, nation: NationState) -> str:
        """Report public satisfaction level."""
        if nation.public_satisfaction < 20:
            context = "Morale is critically low. Military setbacks increase insurrection risk."
        else:
            context = "Public satisfaction is below average. Military losses may decrease it further."

        return f"""## Morale
**Public Satisfaction: {nation.public_satisfaction:.0f}%**

{context}"""

    def _build_strategic_assessment(self, nation_id: str) -> str:
        """
        Build compact strategic assessment.
        Delegates to MilitaryTranslator to avoid duplication.
        """
        return self.military_translator.analyze_threats(nation_id)
