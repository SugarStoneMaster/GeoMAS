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

    def _get_trust_tier(self, trust: float) -> str:
        """Convert a 0-100 trust score into a qualitative bucket (7 tiers)."""
        if trust < 15:
            return "Extremely Low"
        elif trust < 29:
            return "Low"
        elif trust < 43:
            return "Moderately Low"
        elif trust < 58:
            return "Neutral"
        elif trust < 72:
            return "Moderately High"
        elif trust < 86:
            return "High"
        else:
            return "Extremely High"

    def _build_month_header(self, turn: int) -> str:
        """Build a standardized month/turn header."""
        return f"## Month {turn}"

    def _build_relationships(self, nation_id: str, show_cooldowns: bool = False) -> str:
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
            trust_tier = self._get_trust_tier(trust)
            
            line = f"- **{other_nation.name}** ({other_id}): {rel}, Trust: {trust_tier}"
            
            # Show if they are a nuclear power (Deterrence)
            if other_nation.nukes > 0:
                line += " [NUCLEAR POWER] ☢️"
            
            # Show cooldown if requested (e.g., for Foreign Minister)
            if show_cooldowns:
                sender_nation = self.world.nations[nation_id]
                last_turn = sender_nation.message_cooldown.get(other_id, -99)
                cooldown_left = 5 - (self.world.turn - last_turn) # 5 = default cooldown
                if cooldown_left > 0:
                    line += f" [Message Cooldown: {cooldown_left} turns]"
            
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
            
        # Add Global Treaty Network (Third-party alliances)
        global_network = self._build_global_treaty_network(nation_id)
        if global_network:
            lines.append("\n" + global_network)
            
        return "\n".join(lines)

    def _build_global_treaty_network(self, nation_id: str) -> str:
        """
        Build a list of all active treaties and wars between third-party nations.
        """
        lines = ["### GLOBAL DIPLOMATIC NETWORK (Third-Party Relations)"]
        alliances = []
        wars = []
        
        # We need a stable order for determinism
        sorted_nation_ids = sorted(self.world.nations.keys())
        processed_pairs = set()
        
        for i, id1 in enumerate(sorted_nation_ids):
            if id1 == nation_id:
                continue
            
            for id2 in sorted_nation_ids[i+1:]:
                if id2 == nation_id:
                    continue
                
                # Check relationship
                rel = self.world.relationship_matrix.get(id1, {}).get(id2, RelationshipState.PEACE)
                name1 = self.world.nations[id1].name
                name2 = self.world.nations[id2].name
                
                if rel in [RelationshipState.NON_AGGRESSION, RelationshipState.MUTUAL_DEFENSE]:
                    alliances.append(f"- **{name1}** & **{name2}**: {rel}")
                elif rel == RelationshipState.WAR:
                    wars.append(f"- **{name1}** & **{name2}**: {rel} ⚔️")
        
        if not alliances and not wars:
            return ""
            
        if alliances:
            lines.append("#### Treaties")
            lines.extend(alliances)
        if wars:
            lines.append("#### Conflicts")
            lines.extend(wars)
            
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
            
            lines.append(f"- **{other.name}** ({other_id}): Power: {power_desc} | Neighbor: {is_neighbor} | Resources: {res_desc}")
            
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
        
        # Deduplication Logic: Hide actions that are already covered by detailed successful events
        filtered_action_lines = []
        for a_line in action_lines:
            # Check if this action turn and approximate type is in event_lines
            # action format: "Turn X [Domain]: Action → SUCCESS"
            # event format: "Turn X: Summary..."
            duplicate_found = False
            for e_line in event_lines:
                if e_line.startswith(a_line.split("[")[0]): # Match "Turn X: "
                    # Check if summaries are similar (heuristic)
                    # Use a simpler check: if it's the same turn and we have an event, 
                    # it's usually better to show the event.
                    # We only deduplicate if the action was SUCCESS/ACCEPTED.
                    if "→ SUCCESS" in a_line or "→ ACCEPTED" in a_line:
                        duplicate_found = True
                        break
            
            if not duplicate_found:
                filtered_action_lines.append(a_line)

        if filtered_action_lines:
            lines.append(f"### Recent {domain or ''} Actions".replace("  ", " "))
            lines.extend([f"- {a}" for a in filtered_action_lines])
            
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
            
        lines = ["## ACTIVE STRATEGIC CONSTRAINTS (MANDATORY)"]
        lines.append("The Supreme Council has imposed the following directives for this turn. As President, you MUST ensure your Cabinet follows these instructions:")
        
        for inj in injections:
            if inj:
                lines.append(f"- **DIRECTIVE**: {inj.upper()}")
                
        lines.append("\n**Presidential Override**: If a Minister proposes an action that violates these directives, you MUST use your **VETO** power.")
        return "\n".join(lines)

    def _sanitize_prompt(self, text: str) -> str:
        """
        Remove emojis from the prompt text. Emojis are useful for terminal debugging
        but they waste tokens and can confuse the LLM.
        """
        import re
        # Regex capturing most standard emojis and graphical symbols
        emoji_pattern = re.compile(r"[\U00010000-\U0010ffff\u2600-\u27bf]")
        
        # We also manually remove some common ascii/unicode symbols used as graphics
        sanitized = emoji_pattern.sub(r"", text)
        sanitized = re.sub(r" +", " ", sanitized) # Clean up multiple spaces left by removed emojis
        return sanitized.strip()

