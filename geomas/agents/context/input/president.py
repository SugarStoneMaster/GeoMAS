"""
President Input Builder.

Generates dynamic context for the President agent.
Receives summaries from all ministers, relationships, and notable events.
"""

from typing import Optional, List, Dict, Any
from geomas.schemas.world import WorldState, NationState


class PresidentInputBuilder:
    """
    Builds dynamic input context for the President agent.
    
    The President receives:
    - Current state summary (resources, satisfaction, military overview)
    - Summary reports from ministers (not full details)
    - Relationship summaries with all neighbors
    - Recent notable events
    """
    
    def __init__(self, world: WorldState):
        self.world = world
    
    def build(
        self,
        nation_id: str,
        turn: int,
        context_manager: Optional['ContextManager'] = None,
        defense_summary: Optional[str] = None,
        economy_summary: Optional[str] = None,
        foreign_summary: Optional[str] = None,
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
            
        Returns:
            Formatted input prompt (~2800 tokens max)
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # 0. Metadata Header
        sections.append(f"## Month {turn}")
        
        # 1. Cabinet Common: Relationships
        if context_manager:
            sections.append(self._build_diplomatic_relationships(nation_id, context_manager))
        
        # 2. Cabinet Common: Other Nations
        sections.append(self._build_other_nations(nation_id))
        
        # 3. Your Nation Status (Detailed)
        sections.append(self._build_state_overview(nation))
        
        # 4. Minister Briefings
        sections.append(self._build_minister_reports(
            defense_summary, economy_summary, foreign_summary
        ))
        
        # 5. World Events (Global News)
        if context_manager:
            sections.append(self._build_world_events(nation_id, context_manager))
        
        # 6. Your History (High-Level Events relevant to nation)
        if context_manager:
            sections.append(self._build_self_history(nation_id, context_manager))
            
        # 7. Your Recent Decisions (President's domain actions)
        if context_manager:
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
        
        return f"""## Your nation status
**Budget:** {nation.total_budget:,.0f}
**Provinces:** {len(nation.province_ids)} land, {len(nation.territorial_water_ids)} territorial waters
**Resources:** Food {nation.total_food:+.0f}/turn | Energy {nation.total_energy:+.0f}/turn | Materials {nation.total_materials:+.0f}/turn
**Military:** {military_total:,} total forces ({nation.total_soldiers:,} ground, {nation.total_aircraft:,} air, {nation.total_navy:,} naval)
**Population:** {nation.total_population:,} | Satisfaction: {nation.public_satisfaction:.0f}% ({sat_status}){nuke_line}"""

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

    def _build_diplomatic_relationships(self, nation_id: str, cm: 'ContextManager') -> str:
        """Standardized relationship layer."""
        lines = ["## Diplomatic relationships"]
        rel_lines = cm.get_relationships_for(nation_id)
        if rel_lines:
            lines.extend(rel_lines)
        else:
            lines.append("- No established diplomatic records.")
        return "\n".join(lines)

    def _build_other_nations(self, nation_id: str) -> str:
        """
        Standardized other nations layer.
        Compact pipe-separated format.
        """
        from geomas.world.spatial.manager import SpatialManager
        
        lines = ["## Other nations"]
        my_nation = self.world.nations[nation_id]
        my_power = max(0.1, my_nation.power_projection)
        
        spatial = SpatialManager(self.world)
        neighbors = spatial.get_neighboring_nations(nation_id)
        
        # Calculate world averages for resources
        n_nations = len(self.world.nations)
        avg_food = sum(n.total_food for n in self.world.nations.values()) / n_nations
        avg_energy = sum(n.total_energy for n in self.world.nations.values()) / n_nations
        avg_materials = sum(n.total_materials for n in self.world.nations.values()) / n_nations
        
        from geomas.schemas.world import RelationshipState
        
        for other_id, other in self.world.nations.items():
            if other_id == nation_id:
                continue
            
            # Power
            ratio = other.power_projection / my_power
            if ratio > 1.5: power_desc = "Much stronger"
            elif ratio > 1.1: power_desc = "Stronger"
            elif ratio > 0.9: power_desc = "Equal"
            elif ratio > 0.5: power_desc = "Weaker"
            else: power_desc = "Much weaker"
            
            # Neighbors
            is_neighbor = "Yes" if other_id in neighbors else "No"
            
            # Resources
            res_tags = []
            if other.total_food > avg_food * 1.5: res_tags.append("Abundant Food")
            elif other.total_food < avg_food * 0.5: res_tags.append("Food Shortage")
            if other.total_energy > avg_energy * 1.5: res_tags.append("Abundant Energy")
            elif other.total_energy < avg_energy * 0.5: res_tags.append("Energy Shortage")
            if other.total_materials > avg_materials * 1.5: res_tags.append("Abundant Materials")
            elif other.total_materials < avg_materials * 0.5: res_tags.append("Materials Shortage")
            res_desc = ", ".join(res_tags) if res_tags else "Balanced"
            
            # Alliances
            allies = []
            if other_id in self.world.relationship_matrix:
                for target_id, rel in self.world.relationship_matrix[other_id].items():
                    if rel == RelationshipState.ALLIANCE and target_id in self.world.nations:
                        allies.append(self.world.nations[target_id].name)
            allies_desc = ", ".join(allies) if allies else "None"
            
            lines.append(f"- **{other.name}** ({other_id}): Power: {power_desc} | Neighbor: {is_neighbor} | Resources: {res_desc} | Allies: {allies_desc}")
            
        return "\n".join(lines)

    def _build_world_events(self, nation_id: str, cm: 'ContextManager') -> str:
        """Standard world events layer."""
        lines = ["## World events"]
        event_lines = cm.get_events_for(nation_id, max_events=10)
        if event_lines:
            lines.extend(event_lines)
        else:
            lines.append("- No notable world events.")
        return "\n".join(lines)

    def _build_self_history(self, nation_id: str, cm: 'ContextManager') -> str:
        """
        High-level nation history.
        Includes all relevant world events (not Domain filtered).
        """
        lines = ["## Your history"]
        event_lines = cm.get_events_for(nation_id, max_events=15)
        if event_lines:
            lines.extend(event_lines)
        else:
            lines.append("- No significant historical events recorded.")
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
