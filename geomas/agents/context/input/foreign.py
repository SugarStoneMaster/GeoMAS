"""
Foreign Minister Input Builder.

Generates dynamic context for the Foreign Minister agent.
Includes full relationship details, diplomatic proposals, and trust matrix.
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from geomas.schemas.world import WorldState, NationState
from geomas.agents.context.input.base import BaseInputBuilder

if TYPE_CHECKING:
    from geomas.agents.context.events import ContextManager


class ForeignInputBuilder(BaseInputBuilder):
    """
    Builds dynamic input context for the Foreign Minister agent.
    
    The Foreign Minister receives:
    - Full relationship matrix with all nations
    - Trust levels and trends
    - Pending diplomatic proposals
    - Recent diplomatic events
    - Power comparison with neighbors
    """
    
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
            turn: Current turn
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
        sections.append(self._build_month_header(turn))

        # 1b. CRITICAL: Call to Arms (Priority notification)
        if context_manager:
            cta = self._build_call_to_arms_header(nation_id, context_manager)
            if cta:
                sections.append(cta)
        
        # 2. Common Layers
        sections.append(self._build_relationships(nation_id))
        sections.append(self._build_other_nations(nation_id))
        
        # 3. Recent World Events & Feedback
        if context_manager:
            feedback = self._build_presidential_feedback(nation_id, "Foreign", context_manager)
            if feedback:
                sections.append(feedback)
            
            sections.append(self._build_world_events(nation_id, context_manager))
            sections.append(self._build_self_history(nation_id, context_manager, domain="Foreign"))
        
        # 4. Inbox (Specialized)
        if context_manager:
            sections.append(self._build_incoming_messages(nation_id, turn, context_manager))
        
        # 5. Pending Proposals
        sections.append(self._build_pending_proposals(nation))
        
        # 6. Sent Proposals
        if nation.sent_proposals:
            sections.append(self._build_sent_proposals(nation))
        
        return "\n\n".join(sections)

    def _build_call_to_arms_header(self, nation_id: str, cm: 'ContextManager') -> str:
        """Scan for CALL_TO_ARMS targeting this nation and create a loud header."""
        events = cm.get_events_for(nation_id, max_events=10)
        cta_events = [e for e in events if "[CALL_TO_ARMS]" in e and nation_id in e]
        
        if not cta_events:
            return ""
            
        lines = ["# 🚨 CRITICAL: CALL TO ARMS 🚨"]
        lines.append("You have been formally summoned by an ally to join a war. Failing to honor a MUTUAL_DEFENSE pact will result in severe trust penalties.")
        for e in cta_events:
            lines.append(f"- **{e}**")
        return "\n".join(lines)

    def _build_incoming_messages(self, nation_id: str, current_turn: int, cm: 'ContextManager') -> str:
        """
        Build list of recent diplomatic messages (Inbox).
        Shows messages from the current turn and the immediately preceding turn.
        """
        from geomas.agents.context.events.schemas import EventType
        
        lines = ["## Inbox"]
        
        # Filter:
        # 1. Turn >= current_turn - 1
        # 2. Event Type = DIPLOMATIC_MESSAGE
        # 3. Actors include self (recipient)
        
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
                
            messages.append(e)
            
        if not messages:
            return "" # Don't show empty section to save tokens
            
        for m in messages:
            lines.append(f"- {m.to_prompt_line()}")
            
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
                tier = p.get("tier")
                
                # Get target name
                to_name = self.world.nations.get(to_id, {})
                if hasattr(to_name, 'name'): to_name = to_name.name
                else: to_name = to_id
                
                tier_str = f" ({tier})" if tier else ""
                lines.append(f"- ⏳ **{p_type}{tier_str} to {to_name}** (Sent Turn {turn}). Status: **PENDING**")
        
        # 2. Proposal History
        if history:
            lines.append("\n## Proposal history")
            for p in history:
                p_type = p.get("type", "UNKNOWN")
                to_id = p.get("to", "UNKNOWN")
                turn = p.get("turn", "?")
                status = p.get("status", "UNKNOWN")
                resolved_turn = p.get("resolved_turn", "?")
                tier = p.get("tier")
                
                icon = "❓"
                if status == "ACCEPTED": icon = "✅"
                elif status == "REJECTED": icon = "❌"
                elif status == "EXPIRED": icon = "🏚️"
                
                # Get target name
                to_name = self.world.nations.get(to_id, {})
                if hasattr(to_name, 'name'): to_name = to_name.name
                else: to_name = to_id
                
                tier_str = f" ({tier})" if tier else ""
                lines.append(f"- {icon} **{p_type}{tier_str} to {to_name}** (Sent T{turn}, Resolved T{resolved_turn}): **{status}**")
            
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
            tier = proposal.get("tier")
            
            from_name = self.world.nations.get(from_nation, {})
            if hasattr(from_name, 'name'):
                from_name = from_name.name
            else:
                from_name = from_nation
            
            tier_str = f" [{tier}]" if tier else ""
            lines.append(f"\n**{p_type}{tier_str} proposal from {from_name}** (Turn {turn})")
            p_id = proposal.get("id", "MISSING_ID")
            lines.append(f"  [ID: {p_id}]")
            message = proposal.get("message")
            if message:
                lines.append(f"  > \"{message}\"")
            lines.append(f"  → To respond: proposal_id=\"{p_id}\", response=ACCEPT/REJECT")
        
        lines.append("\n⚠️ Ignoring proposals damages trust.")
        
        return "\n".join(lines)
    
