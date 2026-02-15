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
        sections.append(f"## Month {turn}")
        
        # 2. Common Layers (Relationships, Other nations, Events)
        sections.append(self._build_relationships(nation_id))
        sections.append(self._build_other_nations(nation_id))
        
        if context_manager:
            sections.append(self._build_world_events(nation_id, context_manager))
            sections.append(self._build_self_history(nation_id, context_manager))
        
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
            "## Military budget",
            f"**Available Treasury:** {nation.total_budget:,.0f}",
            "",
            "**Creation Costs (Budget / Materials / Energy / Pop):**",
            f"- Soldier: {s_cost['budget']:.0f} / {s_cost['materials']:.0f} / {s_cost['energy']:.0f} / {s_cost['population']} → Can afford: {affordable_soldiers:,}",
            f"- Aircraft: {a_cost['budget']:.0f} / {a_cost['materials']:.0f} / {a_cost['energy']:.0f} / {a_cost['population']} → Can afford: {affordable_aircraft:,}",
            f"- Navy: {n_cost['budget']:.0f} / {n_cost['materials']:.0f} / {n_cost['energy']:.0f} / {n_cost['population']} → Can afford: {affordable_navy:,}",
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
        """Build status of current enemies."""
        lines = ["## Current conflicts"]
        relationships = self.world.relationship_matrix.get(nation_id, {})
        at_war = []
        
        for other_id, status in relationships.items():
            if other_id not in self.world.nations:
                continue
            if status == "WAR":
                at_war.append(self.world.nations[other_id].name)
        
        if at_war:
            lines.append(f"**AT WAR WITH:** {', '.join(at_war)}")
        else:
            lines.append("**No active wars.**")
        
        return "\n".join(lines)
    
    def _build_morale_warning(self, nation: NationState) -> str:
        """Build morale warning for low satisfaction."""
        if nation.public_satisfaction < 20:
            severity = "CRITICAL"
            advice = "Avoid offensive operations. Focus on defense. A defeat could trigger collapse."
        else:
            severity = "WARNING"
            advice = "Military setbacks will be poorly tolerated. Consider war costs carefully."
        
        return f"""## Morale
**Public Satisfaction: {nation.public_satisfaction:.0f}%**

{advice}"""

    def _build_strategic_assessment(self, nation_id: str) -> str:
        """
        Build compact strategic assessment.
        Delegates to MilitaryTranslator to avoid duplication.
        """
        return self.military_translator.analyze_threats(nation_id)

    def _build_other_nations(self, nation_id: str) -> str:
        """
        Build overview of all other nations.
        Includes Power, Neighbors, Resource status, and Alliances.
        """
        from geomas.world.spatial.manager import SpatialManager
        from geomas.schemas.world import RelationshipState
        
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
        
        for other_id, other in self.world.nations.items():
            if other_id == nation_id:
                continue
            
            # 1. Power projection
            ratio = other.power_projection / my_power
            if ratio > 1.5: power_desc = "Much stronger"
            elif ratio > 1.1: power_desc = "Stronger"
            elif ratio > 0.9: power_desc = "Equal"
            elif ratio > 0.5: power_desc = "Weaker"
            else: power_desc = "Much weaker"
            
            # 2. Neighbors
            is_neighbor = "Yes" if other_id in neighbors else "No"
            
            # 3. Resources (Identify significant surplus/deficit)
            res_tags = []
            if other.total_food > avg_food * 1.5: res_tags.append("Abundant Food")
            elif other.total_food < avg_food * 0.5: res_tags.append("Food Shortage")
            
            if other.total_energy > avg_energy * 1.5: res_tags.append("Abundant Energy")
            elif other.total_energy < avg_energy * 0.5: res_tags.append("Energy Shortage")
            
            if other.total_materials > avg_materials * 1.5: res_tags.append("Abundant Materials")
            elif other.total_materials < avg_materials * 0.5: res_tags.append("Materials Shortage")
            
            res_desc = ", ".join(res_tags) if res_tags else "Balanced"
            
            # 4. Alliances (Find who they are allied with)
            allies = []
            if other_id in self.world.relationship_matrix:
                for target_id, rel in self.world.relationship_matrix[other_id].items():
                    if rel == RelationshipState.ALLIANCE and target_id in self.world.nations:
                        allies.append(self.world.nations[target_id].name)
            
            allies_desc = ", ".join(allies) if allies else "None"
            
            lines.append(f"- **{other.name}** ({other_id}): Power: {power_desc} | Neighbor: {is_neighbor} | Resources: {res_desc} | Allies: {allies_desc}")
            
        return "\n".join(lines)

    def _build_relationships(self, nation_id: str) -> str:
        """Build compact relationship matrix."""
        lines = ["## Diplomatic relationships"]
        
        at_war = []
        allies = []
        neutral = []
        
        for other_id, other_nation in self.world.nations.items():
            if other_id == nation_id:
                continue
                
            rel = self.world.relationship_matrix.get(nation_id, {}).get(other_id, "PEACE")
            trust = self.world.trust_matrix.get(nation_id, {}).get(other_id, 50.0)
            
            line = f"- **{other_nation.name}** ({other_id}): {rel}, Trust {trust:.0f}"
            
            if rel == "WAR":
                at_war.append(line)
            elif rel == "ALLIANCE":
                allies.append(line)
            else:
                neutral.append(line)
        
        if at_war:
            lines.append("### AT WAR")
            lines.extend(at_war)
        if allies:
            lines.append("### ALLIES")
            lines.extend(allies)
        if neutral:
            lines.append("### NEUTRAL")
            lines.extend(neutral)
            
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
        """Build domain-specific history for Defense Minister."""
        from geomas.agents.context.events.schemas import EventType
        
        lines = ["## Your history"]
        
        # 1. Defense Actions
        action_lines = cm.get_actions_for(nation_id, domain="Defense", max_actions=8)
        
        # 2. Defense-related Events
        defense_event_types = [
            EventType.WAR_DECLARED,
            EventType.PEACE_SIGNED,
            EventType.ATTACK,
            EventType.TERRITORY_LOST,
            EventType.TERRITORY_GAINED,
            EventType.NUCLEAR_STRIKE,
            EventType.TROOPS_MOBILIZED
        ]
        event_lines = cm.get_events_for(nation_id, max_events=8, event_types=defense_event_types)
        
        if action_lines:
            lines.append("### Recent Actions")
            lines.extend([f"- {a}" for a in action_lines])
            
        if event_lines:
            lines.append("### Notable Defense Events")
            lines.extend([f"- {e}" for e in event_lines])
            
        if not action_lines and not event_lines:
            lines.append("- No recent military history.")
            
        return "\n".join(lines)
