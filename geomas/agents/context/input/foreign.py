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
        
        # 2b. War Status (New)
        war_status = self._build_war_status(nation_id)
        if war_status:
            sections.append(war_status)
        
        # 3. Recent World Events & Feedback
        if context_manager:
            feedback = self._build_presidential_feedback(nation_id, "Foreign", context_manager)
            if feedback:
                sections.append(feedback)
            
            sections.append(self._build_world_events(nation_id, context_manager))
            sections.append(self._build_self_history(nation_id, context_manager, domain="Foreign"))
        
        # 3b. Treaty Opportunities (New)
        opportunities = self._build_treaty_opportunities(nation_id)
        if opportunities:
            sections.append(opportunities)

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
            
        lines = ["# 🚨 CRITICAL: CALL TO ARMS - MUTUAL DEFENSE PACT ACTIVATED 🚨"]
        lines.append("An ally has been attacked. Under the MUTUAL_DEFENSE treaty, you are expected to declare war on the aggressor.")
        lines.append("")
        lines.append("**⚠️ CONSEQUENCES OF INACTION:**")
        lines.append("- If you ignore this for **3 consecutive turns**, your alliance will be AUTOMATICALLY BROKEN.")
        lines.append("- **Global Trust Penalty**: All nations will reduce trust in you by **-30** (Reputation: Unreliable).")
        lines.append("")
        lines.append("To honor the pact: Use `FORMAL_DECLARATION_OF_WAR` against the aggressor.")
        for e in cta_events:
            lines.append(f"- {e}")
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
                
                # Extract tier value if it's an enum
                tier_value = tier.value if hasattr(tier, 'value') else tier
                tier_str = f" ({tier_value})" if tier else ""
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
                
                # Extract tier value if it's an enum
                tier_value = tier.value if hasattr(tier, 'value') else tier
                tier_str = f" ({tier_value})" if tier else ""
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
            
            # Extract tier value if it's an enum
            tier_value = tier.value if hasattr(tier, 'value') else tier
            tier_str = f" [{tier_value}]" if tier else ""
            lines.append(f"\n**{p_type}{tier_str} proposal from {from_name}** (Turn {turn})")
            p_id = proposal.get("id", "MISSING_ID")
            lines.append(f"  [ID: {p_id}]")
            message = proposal.get("message")
            if message:
                lines.append(f"  > \"{message}\"")
            lines.append(f"  → To respond: proposal_id=\"{p_id}\", response=ACCEPT/REJECT")
        
        lines.append("\n⚠️ Ignoring proposals damages trust.")
        
        return "\n".join(lines)
    
    def _build_treaty_opportunities(self, nation_id: str) -> str:
        """Scan trust levels and relationships to suggest viable treaty upgrades."""
        lines = ["## Strategic Opportunities (Treaties)"]
        
        from geomas.schemas.world import RelationshipState
        
        my_trust = self.world.trust_matrix.get(nation_id, {})
        my_rels = self.world.relationship_matrix.get(nation_id, {})
        
        opportunities = []
        
        # Get set of nations involved in pending proposals (sent or received)
        nation = self.world.nations.get(nation_id)
        pending_targets = set()
        
        if nation:
            # Check sent proposals (we asked them)
            for p in nation.sent_proposals:
                if p.get("status") == "PENDING":
                    pending_targets.add(p.get("to"))
            
            # Check received proposals (they asked us)
            for p in nation.pending_proposals:
                pending_targets.add(p.get("from"))
        
        for other_id in self.world.nations:
            if other_id == nation_id:
                continue
            
            # Skip if we already have a pending proposal with them
            if other_id in pending_targets:
                continue
                
            trust = my_trust.get(other_id, 50)
            rel = my_rels.get(other_id, RelationshipState.PEACE)
            
            # Extract relation value if enum
            rel_val = rel.value if hasattr(rel, 'value') else rel
            
            if rel_val == "PEACE":
                if trust >= 80:
                     opportunities.append(f"- **{other_id}** (Trust {trust}): High trust. Viable for **MUTUAL_DEFENSE** or **NON_AGGRESSION**.")
                elif trust >= 60:
                     opportunities.append(f"- **{other_id}** (Trust {trust}): Good trust. Viable for **NON_AGGRESSION** pact.")
            
            elif rel_val == "NON_AGGRESSION":
                if trust >= 75:
                     opportunities.append(f"- **{other_id}** (Trust {trust}): Very high trust. Consider upgrading to **MUTUAL_DEFENSE**.")
        
        if not opportunities:
            return ""
            
        lines.extend(opportunities)
        lines.extend(opportunities)
        lines.append("To enact these, use `PROPOSE_ALLIANCE` with the specific `treaty_tier`.")
        return "\n".join(lines)

    def _build_war_status(self, nation_id: str) -> str:
        """Build status of active wars for diplomatic context."""
        lines = ["## ⚔️ Active War Status"]
        relationships = self.world.relationship_matrix.get(nation_id, {})
        nation = self.world.nations.get(nation_id)
        
        at_war = False
        
        for other_id, status in relationships.items():
            if status == "WAR":
                at_war = True
                enemy_name = self.world.nations[other_id].name
                
                # Get War Stats
                stats = nation.active_wars.get(other_id)
                if stats:
                    duration = self.world.turn - stats.start_turn
                    lost = stats.lost_provinces
                    original = stats.original_provinces
                    
                    if original > 0:
                        loss_pct = (lost / original) * 100
                    else:
                        loss_pct = 0
                        
                    lines.append(f"### WAR with {enemy_name} ({other_id})")
                    lines.append(f"- **Duration**: {duration} turns")
                    lines.append(f"- **Territory Lost**: {lost} ({loss_pct:.1f}% of nation!)")
                    lines.append(f"- **Territory Conquered**: {stats.conquered_provinces}")

                else:
                    lines.append(f"### WAR with {enemy_name} (Fresh conflict)")

        if not at_war:
            return "" # No section if no wars
            
        return "\n".join(lines)
