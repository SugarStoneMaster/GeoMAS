"""
Foreign Minister Input Builder.

Generates dynamic context for the Foreign Minister agent.
Includes full relationship details, diplomatic proposals, and trust matrix.
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from geomas.schemas.world import WorldState, NationState

if TYPE_CHECKING:
    from geomas.agents.context.events import ContextManager

class ForeignInputBuilder:
    """
    Builds dynamic input context for the Foreign Minister agent.
    
    The Foreign Minister receives:
    - Full relationship matrix with all nations
    - Trust levels and trends
    - Pending diplomatic proposals
    - Recent diplomatic events
    - Power comparison with neighbors
    """
    
    def __init__(self, world: WorldState):
        self.world = world
    
    def build(
        self,
        nation_id: str,
        turn: int,
        recent_events: Optional[List[str]] = None,
        recent_actions: Optional[List[str]] = None,
        context_manager: Optional['ContextManager'] = None,
    ) -> str:
        """
        Build the input context for the Foreign Minister.
        
        Args:
            nation_id: Nation ID
            recent_events: List of recent diplomatic events (Legacy, prefer context_manager)
            recent_actions: List of recent diplomatic actions (Legacy, prefer context_manager)
            context_manager: Event Context Manager source
            
        Returns:
            Formatted input prompt (~2000 tokens max)
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # 1. Month Header
        sections.append(f"## Month {turn}")
        
        # 2. Diplomatic Relationships
        sections.append(self._build_relationships(nation_id))
        
        # 3. Other nations
        sections.append(self._build_other_nations(nation_id))
        
        # 4. Recent World Events
        if context_manager:
            sections.append(self._build_world_events(nation_id, context_manager))
        elif recent_events:
            sections.append(self._build_events(recent_events))
            
        # 5. Your History (Foreign focus)
        if context_manager:
            sections.append(self._build_self_history(nation_id, context_manager))
        elif recent_actions:
            sections.append(self._build_recent_actions(recent_actions))
            
        # 6. Inbox
        if context_manager:
            sections.append(self._build_incoming_messages(nation_id, turn, context_manager))
        
        # 7. Pending Proposals
        sections.append(self._build_pending_proposals(nation))
        
        # 8. Sent Proposals
        if nation.sent_proposals:
            sections.append(self._build_sent_proposals(nation))
        
        return "\n\n".join(sections)

    def _build_incoming_messages(self, nation_id: str, current_turn: int, cm: 'ContextManager') -> str:
        """
        Build list of recent diplomatic messages (Inbox).
        Shows messages from the current turn and the immediately preceding turn.
        """
        from geomas.agents.context.events.schemas import EventType
        
        lines = ["## Inbox"]
        
        # Filter:
        # 1. Event Type = DIPLOMATIC_MESSAGE
        # 2. Actors include self (recipient)
        # 3. Turn >= current_turn - 1
        
        events = cm.global_events
        messages = []
        
        for e in events:
            if e.event_type != EventType.DIPLOMATIC_MESSAGE:
                continue
                
            if current_turn - e.turn > 1:
                continue
                
            # Must be a participant
            if not e.actors or nation_id not in e.actors:
                continue
                
            # If self is the ONLY actor (talking to self?), skip.
            # Usually actors=[sender, target].
            # We want to know WHO sent it.
            # Parse summary? "Nation A sent a PRAISE to Nation B"
            
            messages.append(e)
            
        if not messages:
            return "" # Don't show empty section to save tokens
            
        for m in messages:
            lines.append(f"- {m.to_prompt_line()}")
            
        return "\n".join(lines)

    def _build_world_events(self, nation_id: str, cm: 'ContextManager') -> str:
        """
        Build world events (News) excluding self.
        """
        lines = ["## World events"]
        
        # Get global events
        events = cm.global_events
        
        # Filter: Self is NOT an actor
        world_events = []
        for e in events:
            # Check if self is actor
            is_actor = False
            if e.actors:
                if nation_id in e.actors:
                    is_actor = True
            
            if not is_actor:
                world_events.append(e)
        
        # Sort by Turn descending (newest first)
        world_events.sort(key=lambda x: x.turn, reverse=True)
        
        # Take top 15
        for e in world_events[:15]:
            lines.append(f"- {e.to_prompt_line()}")
            
        if len(lines) == 1:
            lines.append("No major world events.")
            
        return "\n".join(lines)

    def _build_self_history(self, nation_id: str, cm: 'ContextManager') -> str:
        """
        Build unified history for the nation.
        
        Rules:
        - Foreign: Actions (MyAction) + Events (NotableEvent)
        - Defense/Economy: Events ONLY (NotableEvent) - High level abstracts
        """
        lines = ["## Your history"]
        
        history_items = []
        
        # 1. Get Actions (Foreign Only)
        if nation_id in cm.nation_actions:
            actions = cm.nation_actions[nation_id]
            for a in actions:
                if a.domain == "Foreign":
                    history_items.append({
                        "turn": a.turn,
                        "text": a.to_prompt_line(),
                        "type": "ACTION"
                    })
        
        # 2. Get Events (All domains where self is actor)
        events = cm.global_events
        for e in events:
            is_actor = False
            if e.actors and nation_id in e.actors:
                is_actor = True
            
            if is_actor:
                history_items.append({
                    "turn": e.turn,
                    "text": e.to_prompt_line(),
                    "type": "EVENT"
                })
        
        # Sort by Turn descending (Newest first)
        history_items.sort(key=lambda x: x["turn"], reverse=True)
        
        # Take top 25
        for item in history_items[:25]:
            lines.append(f"- {item['text']}")
            
        if len(lines) == 1:
            lines.append("No history yet.")
            
        return "\n".join(lines)
    def _build_sent_proposals(self, nation: NationState) -> str:
        """Build list of proposals sent by us (Active + History)."""
        active = []
        history = []
        
        for p in nation.sent_proposals:
            status = p.get("status", "PENDING")
            if status == "PENDING":
                active.append(p)
            else:
                history.append(p)
        
        # Sort history by resolved_turn descending (newest first)
        history.sort(key=lambda x: x.get("resolved_turn", 0), reverse=True)
        
        lines = []
        
        # 1. Active Proposals
        if active:
            lines.append("## Sent proposals")
            for p in active:
                p_type = p.get("type", "UNKNOWN")
                to_id = p.get("to", "UNKNOWN")
                turn = p.get("turn", "?")
                
                # Get target name
                to_name = self.world.nations.get(to_id, {})
                if hasattr(to_name, 'name'): to_name = to_name.name
                else: to_name = to_id
                
                lines.append(f"- ⏳ **{p_type} to {to_name}** (Sent Turn {turn}). Status: **PENDING**")
        
        # 2. Proposal History
        if history:
            lines.append("\n## Proposal history")
            for p in history:
                p_type = p.get("type", "UNKNOWN")
                to_id = p.get("to", "UNKNOWN")
                turn = p.get("turn", "?")
                status = p.get("status", "UNKNOWN")
                resolved_turn = p.get("resolved_turn", "?")
                
                icon = "❓"
                if status == "ACCEPTED": icon = "✅"
                elif status == "REJECTED": icon = "❌"
                elif status == "EXPIRED": icon = "🏚️"
                
                # Get target name
                to_name = self.world.nations.get(to_id, {})
                if hasattr(to_name, 'name'): to_name = to_name.name
                else: to_name = to_id
                
                lines.append(f"- {icon} **{p_type} to {to_name}** (Sent T{turn}, Resolved T{resolved_turn}): **{status}**")
            
        return "\n".join(lines)

    def _build_pending_proposals(self, nation: NationState) -> str:
        """Build pending proposals requiring response."""
        lines = ["## Pending proposals"]
        
        if not nation.pending_proposals:
            lines.append("**No pending proposals. DO NOT generate any `proposal_responses`. Leave `proposal_responses` as an EMPTY list `[]`.**")
            return "\n".join(lines)
        
        for proposal in nation.pending_proposals:
            p_type = proposal.get("type", "Unknown")
            from_nation = proposal.get("from", "Unknown")
            turn = proposal.get("turn", "?")
            
            from_name = self.world.nations.get(from_nation, {})
            if hasattr(from_name, 'name'):
                from_name = from_name.name
            else:
                from_name = from_nation
            
            lines.append(f"\n**{p_type} proposal from {from_name}** (Turn {turn})")
            p_id = proposal.get("id", "MISSING_ID")
            lines.append(f"  [ID: {p_id}]")
            message = proposal.get("message")
            if message:
                lines.append(f"  > \"{message}\"")
            lines.append(f"  → To respond: proposal_id=\"{p_id}\", response=ACCEPT/REJECT")
        
        lines.append("\n⚠️ Ignoring proposals damages trust.")
        
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
            trust_val = self.world.trust_matrix.get(nation_id, {}).get(other_id, 50.0)
            
            line = f"- **{other_nation.name}** ({other_id}): {rel}, Trust {trust_val:.0f}"
            
            if rel == "WAR":
                at_war.append(line)
            elif rel == "ALLIANCE":
                allies.append(line)
            else:
                neutral.append(line)
        
        if at_war:
            lines.append("\n**🔴 AT WAR:**")
            for l in at_war:
                lines.append(f"  {l}")
        
        if allies:
            lines.append("\n**🟢 ALLIES:**")
            for l in allies:
                lines.append(f"  {l}")
            lines.append("\n> ⚠️ You are ALREADY allied with these nations. Do NOT propose alliance to them.")
            
        if neutral:
            lines.append("\n**⚪ NEUTRAL/PEACE:**")
            # Sort by trust descending
            for l in neutral:
                lines.append(f"  {l}")
                
        return "\n".join(lines)
    
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
                        # Only show the name
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
        """Build domain-specific history for Foreign Minister."""
        from geomas.agents.context.events.schemas import EventType
        
        lines = ["## Your history"]
        
        # 1. Foreign Actions
        action_lines = cm.get_actions_for(nation_id, domain="Foreign", max_actions=8)
        
        # 2. Foreign-related Events
        foreign_event_types = [
            EventType.WAR_DECLARED,
            EventType.PEACE_SIGNED,
            EventType.ALLIANCE_FORMED,
            EventType.ALLIANCE_BROKEN,
            EventType.DIPLOMATIC_MESSAGE
        ]
        event_lines = cm.get_events_for(nation_id, max_events=8, event_types=foreign_event_types)
        
        # Combine and sort (conceptually, though get_actions_for and get_events_for already sort)
        # We'll just list them separately or combine if needed. For now, separate is cleaner.
        if action_lines:
            lines.append("### Recent Actions")
            lines.extend([f"- {a}" for a in action_lines])
            
        if event_lines:
            lines.append("### Notable Foreign Events")
            lines.extend([f"- {e}" for e in event_lines])
            
        if not action_lines and not event_lines:
            lines.append("- No recent foreign history.")
            
        return "\n".join(lines)
    
