"""
President Input Builder.

Generates dynamic context for the President agent.
Receives summaries from all ministers, relationships, and notable events.
"""

from typing import Optional, List, TYPE_CHECKING
from geomas.schemas.world import NationState
from geomas.agents.context.input.base import BaseInputBuilder

if TYPE_CHECKING:
    from geomas.agents.context.events import ContextManager


class PresidentInputBuilder(BaseInputBuilder):
    """
    Builds dynamic input context for the President agent.
    
    The President receives:
    - Current state summary (resources, satisfaction, military overview)
    - Summary reports from ministers (not full details)
    - Relationship summaries with all neighbors
    - Recent notable events
    """
    
    def build(
        self,
        nation_id: str,
        turn: int,
        context_manager: Optional['ContextManager'] = None,
        defense_summary: Optional[str] = None,
        economy_summary: Optional[str] = None,
        foreign_summary: Optional[str] = None,
        injections: Optional[List[str]] = None,
    ) -> str:
        """
        Build the input context for the President.
        
        Args:
            nation_id: Nation ID
            turn: Current turn
            context_manager: Memory context manager
            defense_summary: Summary from Defense Minister
            economy_summary: Summary from Economy Minister
            foreign_summary: Summary from Foreign Minister
            injections: Optional list of active strategic constraints
            
        Returns:
            Formatted input prompt (~2800 tokens max)
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # 1. Month Header
        sections.append(self._build_month_header(turn))
        
        # 1b. Active Constraints (XAI Injections)
        if injections:
            sections.append(self._build_active_constraints(injections))
        
        # 2. Common Layers
        sections.append(self._build_relationships(nation_id))
        sections.append(self._build_other_nations(nation_id))
        
        # 3. Your Nation Status (Detailed)
        sections.append(self._build_state_overview(nation))
        
        # 4. Minister Briefings
        sections.append(self._build_minister_reports(
            defense_summary, economy_summary, foreign_summary
        ))
        
        # 5. World Events & History
        if context_manager:
            sections.append(self._build_world_events(nation_id, context_manager))
            sections.append(self._build_self_history(nation_id, context_manager)) # Domain=None for President
            
            # President-specific: Decision history
            sections.append(self._build_recent_decisions(nation_id, context_manager))
        
        return "\n\n".join(sections)
    
    def _build_state_overview(self, nation: NationState) -> str:
        """Detailed nation state overview."""
        military_total = nation.total_soldiers + nation.total_aircraft + nation.total_navy
        
        # Satisfaction status
        if nation.public_satisfaction < 20:
            sat_status = "⚠️ CRITICAL"
        elif nation.public_satisfaction < 40:
            sat_status = "⚠️ LOW"
        elif nation.public_satisfaction < 60:
            sat_status = "STABLE"
        else:
            sat_status = "GOOD"
        
        nuke_line = f"\n**Nuclear Arsenal:** {nation.nukes} warheads" if nation.nukes > 0 else ""
        
        # War Assessment
        war_lines = []
        if nation.active_wars:
            total_lost = sum(w.lost_provinces for w in nation.active_wars.values())
            total_conquered = sum(w.conquered_provinces for w in nation.active_wars.values())
            
            start_provs = len(nation.province_ids) + total_lost - total_conquered
            if start_provs > 0:
                loss_pct = (total_lost - total_conquered) / start_provs * 100
            else:
                loss_pct = 0
            
            war_lines.append(f"\n**WAR OVERVIEW:** Active conflicts with {len(nation.active_wars)} nations.")
            war_lines.append(f"- **Total Territory Change:** -{total_lost} Lost / +{total_conquered} Conquered")
            
            if loss_pct > 15:
                 war_lines.append(f"- **STRATEGIC ALERT:** 🚨 CRISIS. Nation has shrunk by {loss_pct:.1f}%. DEFENSE IS FAILING.")
            elif loss_pct > 5:
                 war_lines.append(f"- **STRATEGIC ALERT:** ⚠️ LOSING GROUND. Trend is negative.")
            elif total_conquered > total_lost:
                 war_lines.append(f"- **STRATEGIC ALERT:** ✅ EXPANDING. War aimed at conquest is succeeding.")

        war_section = "\n".join(war_lines)
        
        return f"""## Your nation status
**Budget:** {nation.total_budget:,.0f}
**Provinces:** {len(nation.province_ids)} land, {len(nation.territorial_water_ids)} territorial waters
**Resources:** Food {nation.total_food:+.0f}/turn | Energy {nation.total_energy:+.0f}/turn | Materials {nation.total_materials:+.0f}/turn
**Military:** {military_total:,} total forces ({nation.total_soldiers:,} ground, {nation.total_aircraft:,} air, {nation.total_navy:,} naval)
**Population:** {nation.total_population:,} | Satisfaction: {nation.public_satisfaction:.0f}% ({sat_status}){nuke_line}{war_section}"""

    def _build_minister_reports(
        self,
        defense: Optional[str],
        economy: Optional[str],
        foreign: Optional[str]
    ) -> str:
        """Build minister summary briefings."""
        lines = ["## Minister briefings"]
        
        if defense:
            lines.append(f"\n**Defense Minister:**\n{defense}")
        else:
            lines.append("\n**Defense Minister:** No report available")
        
        if economy:
            lines.append(f"\n**Economy Minister:**\n{economy}")
        else:
            lines.append("\n**Economy Minister:** No report available")
        
        if foreign:
            lines.append(f"\n**Foreign Minister:**\n{foreign}")
        else:
            lines.append("\n**Foreign Minister:** No report available")
        
        return "\n".join(lines)

    def _build_recent_decisions(self, nation_id: str, cm: 'ContextManager') -> str:
        """
        President's decision history (Approvals/Vetos).
        """
        lines = ["## Your recent decisions"]
        # Retrieve actions for 'President' domain
        action_lines = cm.get_actions_for(nation_id, domain="President", max_actions=15)
        if action_lines:
            lines.extend(action_lines)
        else:
            lines.append("- No recent presidential decisions recorded.")
        return "\n".join(lines)
