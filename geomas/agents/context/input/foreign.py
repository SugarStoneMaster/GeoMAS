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
        
        # Metadata Header for Observability
        sections.append(f"## TURN {turn}")
        
        # 1. Pending Proposals (require response)
        sections.append(self._build_pending_proposals(nation))
        
        # 2. Full Relationship Matrix
        sections.append(self._build_relationships(nation_id))
        
        # 3. Power Balance
        sections.append(self._build_power_balance(nation_id))
        
        # 4. Recent Diplomatic Events (Legacy or ContextManager)
        if context_manager:
            # New De-cluttered History
            sections.append(self._build_world_events(nation_id, context_manager))
            sections.append(self._build_self_history(nation_id, context_manager))
        elif recent_events:
            # Fallback Legacy
            sections.append(self._build_events(recent_events))
        
        # 5. Recent Diplomatic Actions (Legacy Only, ContextManager handles this in self_history)
        if not context_manager and recent_actions:
            sections.append(self._build_recent_actions(recent_actions))
            
        # 6. SENT PROPOSALS (Tracking)
        if nation.sent_proposals:
            sections.append(self._build_sent_proposals(nation))
        
        return "\n\n".join(sections)

    def _build_world_events(self, nation_id: str, cm: 'ContextManager') -> str:
        """
        Build world events (News) excluding self.
        """
        lines = ["## 🌍 WORLD EVENTS (News)"]
        
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
        lines = ["## 📜 YOUR HISTORY (Foreign Actions & World Interactions)"]
        
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
            lines.append("## 📤 SENT PROPOSALS (Awaiting Response)")
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
            lines.append("\n## 📜 PROPOSAL HISTORY (Last 25 Turns)")
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
        lines = ["## 📬 PENDING PROPOSALS (Require Response)"]
        
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
        """Build full relationship matrix."""
        lines = ["## 🌍 DIPLOMATIC RELATIONSHIPS"]
        
        relationships = self.world.relationship_matrix.get(nation_id, {})
        trust = self.world.trust_matrix.get(nation_id, {})
        
        # Group by relationship type
        at_war = []
        allies = []
        neutral = []
        
        for other_id, other_nation in self.world.nations.items():
            if other_id == nation_id:
                continue
            
            rel_status = relationships.get(other_id, "PEACE")
            trust_level = trust.get(other_id, 50.0)
            
            if trust_level >= 80:
                trust_desc = "Exceptional Trust"
            elif trust_level >= 60:
                trust_desc = "Friendly"
            elif trust_level >= 40:
                trust_desc = "Neutral"
            elif trust_level >= 20:
                trust_desc = "Distrustful"
            else:
                trust_desc = "Hostile"
            
            # Use ID primarily
            entry = {
                "id": other_id,
                "trust": trust_level,
                "trust_desc": trust_desc,
                "status": rel_status
            }
            
            if rel_status == "WAR":
                at_war.append(entry)
            elif rel_status == "ALLIANCE":
                allies.append(entry)
            else:
                neutral.append(entry)
        
        # Output by group
        if at_war:
            lines.append("\n**🔴 AT WAR:**")
            for e in at_war:
                lines.append(f"  - **{e['id']}**: Trust {e['trust']:.0f} ({e['trust_desc']})")
        
        if allies:
            lines.append("\n**🟢 ALLIES:**")
            for e in allies:
                lines.append(f"  - **{e['id']}**: Trust {e['trust']:.0f} ({e['trust_desc']})")
            lines.append("\n> ⚠️ You are ALREADY allied with these nations. Do NOT propose alliance to them.")
        
        if neutral:
            lines.append("\n**⚪ NEUTRAL/PEACE:**")
            for e in sorted(neutral, key=lambda x: -x['trust']):
                lines.append(f"  - **{e['id']}**: Trust {e['trust']:.0f} ({e['trust_desc']})")
        
        return "\n".join(lines)
    
    def _build_power_balance(self, nation_id: str) -> str:
        """Build power comparison with neighbors."""
        lines = ["## ⚖️ POWER BALANCE"]
        
        my_power = self.world.nations[nation_id].power_projection
        
        for other_id, other_nation in self.world.nations.items():
            if other_id == nation_id:
                continue
            
            other_power = other_nation.power_projection
            
            if my_power > 0:
                ratio = other_power / my_power
            else:
                ratio = 1.0
            
            if ratio > 1.5:
                comparison = "⚠️ Much stronger"
            elif ratio > 1.1:
                comparison = "Stronger"
            elif ratio > 0.9:
                comparison = "Equal"
            elif ratio > 0.6:
                comparison = "Weaker"
            else:
                comparison = "✅ Much weaker"
            
            lines.append(f"- **{other_nation.name}**: {comparison}")
        
        return "\n".join(lines)
    
    def _build_events(self, events: List[str]) -> str:
        """Build recent diplomatic events."""
        lines = ["## 📰 RECENT DIPLOMATIC EVENTS"]
        for event in events[-8:]:
            lines.append(f"- {event}")
        return "\n".join(lines)
    
    def _build_recent_actions(self, actions: List[str]) -> str:
        """Build recent diplomatic actions."""
        lines = ["## 📋 YOUR RECENT DIPLOMATIC ACTIONS"]
        for action in actions[-5:]:
            lines.append(f"- {action}")
        return "\n".join(lines)
