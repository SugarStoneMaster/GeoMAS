"""
Base Input Builder.

Consolidates common prompt-building logic for all agents.
Ensures consistency in relationship matrices, international overviews, and event logs.
"""

from typing import Optional, List, TYPE_CHECKING
from geomas.schemas.world import WorldState, RelationshipState

if TYPE_CHECKING:
    from geomas.agents.context.events import ContextManager


class BaseInputBuilder:
    """
    Common logic for all agent input builders.
    
    Provides standardized methods for:
    - Month Headers
    - Diplomatic Matrix
    - International Overview
    - World Events
    - Historical Records
    """
    
    def __init__(self, world: WorldState):
        self.world = world

    def _build_month_header(self, turn: int) -> str:
        """Build a standardized month/turn header."""
        return f"## Month {turn}"

    def _build_relationships(self, nation_id: str) -> str:
        """
        Build standard deterministic relationship matrix.
        Shows WAR, ALLIANCE, and NEUTRAL status with Trust levels.
        """
        lines = ["## Diplomatic relationships"]
        
        at_war = []
        allies = []
        neutral = []
        
        for other_id, other_nation in self.world.nations.items():
            if other_id == nation_id:
                continue
                
            rel = self.world.relationship_matrix.get(nation_id, {}).get(other_id, RelationshipState.PEACE)
            trust = self.world.trust_matrix.get(nation_id, {}).get(other_id, 50.0)
            
            line = f"- **{other_nation.name}** ({other_id}): {rel}, Trust {trust:.0f}"
            
            if rel == RelationshipState.WAR:
                at_war.append(line)
            elif rel in [RelationshipState.NON_AGGRESSION, RelationshipState.MUTUAL_DEFENSE]:
                allies.append(line)
            else:
                neutral.append(line)
        
        if at_war:
            lines.append("### AT WAR")
            lines.extend(at_war)
        if allies:
            lines.append("### TREATIES")
            lines.extend(allies)
        if neutral:
            lines.append("### NEUTRAL")
            lines.extend(neutral)
            
        return "\n".join(lines)

    def _build_other_nations(self, nation_id: str) -> str:
        """
        Build verbose overview of all other nations.
        Includes Power projection, Neighbor status, Resource profiles, and Alliances.
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
            
            # 4. Treaties (Find who they are allied with)
            treaties = []
            if other_id in self.world.relationship_matrix:
                for target_id, rel in self.world.relationship_matrix[other_id].items():
                    if rel in [RelationshipState.NON_AGGRESSION, RelationshipState.MUTUAL_DEFENSE] and target_id in self.world.nations:
                        treaties.append(f"{self.world.nations[target_id].name} ({rel})")
            
            treaties_desc = ", ".join(treaties) if treaties else "None"
            
            lines.append(f"- **{other.name}** ({other_id}): Power: {power_desc} | Neighbor: {is_neighbor} | Resources: {res_desc} | Treaties: {treaties_desc}")
            
        return "\n".join(lines)

    def _build_world_events(self, nation_id: str, cm: 'ContextManager') -> str:
        """Standard world events (news) layer split into recent and historical."""
        lines = ["## World events"]
        
        # 1. Breaking News (Pure Recency - max 6)
        recent_events = cm.get_events_for(
            nation_id, 
            current_turn=self.world.turn, 
            max_events=6, 
            use_salience=False
        )
        
        # 2. Historical Context (Salience - max 5)
        salient_events = cm.get_events_for(
            nation_id, 
            current_turn=self.world.turn, 
            max_events=5, 
            use_salience=True
        )
        
        # Filter intersection (don't show a breaking news event twice)
        historical_events = [e for e in salient_events if e not in recent_events]
        
        has_events = False
        
        if recent_events:
            lines.append("### Breaking News")
            lines.extend(recent_events)
            has_events = True
            
        if historical_events:
            lines.append("### Historical Context")
            lines.extend(historical_events)
            has_events = True
            
        if not has_events:
            lines.append("- No notable world events.")
            
        return "\n".join(lines)

    def _build_self_history(
        self, 
        nation_id: str, 
        cm: 'ContextManager', 
        domain: Optional[str] = None
    ) -> str:
        """
        Build history of actions and events for the nation.
        If domain is provided, filters for that specific domain.
        """
        from geomas.agents.context.events.schemas import EventType
        
        lines = ["## Your history"]
        
        # 1. Get Actions (Filtered by domain if provided, using salience to remember important actions)
        action_lines = cm.get_actions_for(
            nation_id, 
            current_turn=self.world.turn,
            domain=domain, 
            max_actions=8,
            use_salience=True
        )
        
        # 2. Get Events (Relevant to domain or general)
        event_types = None
        title_suffix = "History"
        
        if domain == "Defense":
            event_types = [
                EventType.WAR_DECLARED, EventType.PEACE_SIGNED, 
                EventType.ATTACK, EventType.TERRITORY_LOST, EventType.TERRITORY_GAINED,
                EventType.NUCLEAR_STRIKE, EventType.TROOPS_MOBILIZED
            ]
            title_suffix = "Military Events"
        elif domain == "Economy":
            event_types = [EventType.TRADE_DEAL, EventType.ECONOMIC_CRISIS, EventType.CIVIL_UNREST]
            title_suffix = "Economic Events"
        elif domain == "Foreign":
            event_types = [
                EventType.WAR_DECLARED, EventType.PEACE_SIGNED,
                EventType.ALLIANCE_FORMED, EventType.ALLIANCE_BROKEN,
                EventType.DIPLOMATIC_MESSAGE
            ]
            title_suffix = "Foreign Events"
            
        event_lines = cm.get_events_for(
            nation_id, 
            current_turn=self.world.turn, 
            max_events=8, 
            event_types=event_types,
            use_salience=True
        )
        
        if action_lines:
            lines.append(f"### Recent {domain or ''} Actions".replace("  ", " "))
            lines.extend([f"- {a}" for a in action_lines])
            
        if event_lines:
            lines.append(f"### Notable {title_suffix}")
            lines.extend([f"- {e}" for e in event_lines])
            
        if not action_lines and not event_lines:
            lines.append(f"- No recent {domain.lower() if domain else 'significant'} history.")
            
        return "\n".join(lines)

    def _build_presidential_feedback(
        self, 
        nation_id: str, 
        domain: str, 
        cm: 'ContextManager'
    ) -> str:
        """Get instructions/feedback from the President for this domain."""
        feedback = cm.get_presidential_feedback(nation_id, domain)
        return feedback if feedback else ""
    def _build_active_constraints(self, injections: Optional[List[str]] = None) -> str:
        """
        Build a section detailing active constraints (XAI Injections).
        Used to inform the President of mandatory directives.
        """
        if not injections:
            return ""
            
        lines = ["## ⚠️ ACTIVE STRATEGIC CONSTRAINTS (MANDATORY)"]
        lines.append("The Supreme Council has imposed the following directives for this turn. As President, you MUST ensure your Cabinet follows these instructions:")
        
        for inj in injections:
            if inj:
                lines.append(f"- **DIRECTIVE**: {inj.upper()}")
                
        lines.append("\n**Presidential Override**: If a Minister proposes an action that violates these directives, you MUST use your **VETO** power.")
        return "\n".join(lines)
