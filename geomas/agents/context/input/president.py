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
        defense_summary: Optional[str] = None,
        economy_summary: Optional[str] = None,
        foreign_summary: Optional[str] = None,
        recent_events: Optional[List[str]] = None,
        recent_actions: Optional[List[str]] = None,
    ) -> str:
        """
        Build the input context for the President.
        
        Args:
            nation_id: Nation ID
            defense_summary: Summary from Defense Minister
            economy_summary: Summary from Economy Minister
            foreign_summary: Summary from Foreign Minister
            recent_events: List of recent notable events
            recent_actions: List of nation's recent actions
            
        Returns:
            Formatted input prompt (~2500 tokens max)
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # 1. Current State Overview
        sections.append(self._build_state_overview(nation))
        
        # 2. Minister Reports
        sections.append(self._build_minister_reports(
            defense_summary, economy_summary, foreign_summary
        ))
        
        # 3. Relationship Summary
        sections.append(self._build_relationships(nation_id))
        
        # 4. Recent Events
        if recent_events:
            sections.append(self._build_events(recent_events))
        
        # 5. Recent Actions
        if recent_actions:
            sections.append(self._build_actions(recent_actions))
        
        return "\n\n".join(sections)
    
    def _build_state_overview(self, nation: NationState) -> str:
        """Build nation state overview."""
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
        
        return f"""== YOUR NATION STATUS ==
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
        """Build minister summary reports."""
        lines = ["== MINISTER BRIEFINGS =="]
        
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
    
    def _build_relationships(self, nation_id: str) -> str:
        """Build relationship summary with neighbors."""
        lines = ["== YOUR RELATIONSHIPS =="]
        
        nation = self.world.nations[nation_id]
        
        # Get all nations we have relationships with
        if nation_id in self.world.relationship_matrix:
            relationships = self.world.relationship_matrix[nation_id]
        else:
            relationships = {}
        
        if nation_id in self.world.trust_matrix:
            trust = self.world.trust_matrix[nation_id]
        else:
            trust = {}
        
        for other_id, other_nation in self.world.nations.items():
            if other_id == nation_id:
                continue
            
            rel_status = relationships.get(other_id, "PEACE")
            trust_level = trust.get(other_id, 50.0)
            
            # Trust description
            if trust_level >= 80:
                trust_desc = "ally"
            elif trust_level >= 60:
                trust_desc = "friendly"
            elif trust_level >= 40:
                trust_desc = "neutral"
            elif trust_level >= 20:
                trust_desc = "distrustful"
            else:
                trust_desc = "hostile"
            
            lines.append(f"- **{other_nation.name}**: {rel_status}, Trust {trust_level:.0f} ({trust_desc})")
        
        return "\n".join(lines)
    
    def _build_events(self, events: List[str]) -> str:
        """Build recent events section."""
        lines = ["== RECENT WORLD EVENTS =="]
        for event in events[-10:]:  # Last 10 events
            lines.append(f"- {event}")
        return "\n".join(lines)
    
    def _build_actions(self, actions: List[str]) -> str:
        """Build recent actions section."""
        lines = ["== YOUR RECENT ACTIONS =="]
        for action in actions[-10:]:  # Last 10 actions
            lines.append(f"- {action}")
        return "\n".join(lines)
