"""
Foreign Minister Input Builder.

Generates dynamic context for the Foreign Minister agent.
Includes full relationship details, diplomatic proposals, and trust matrix.
"""

from typing import Optional, List, Dict, Any
from geomas.schemas.world import WorldState, NationState


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
        recent_events: Optional[List[str]] = None,
        recent_actions: Optional[List[str]] = None,
    ) -> str:
        """
        Build the input context for the Foreign Minister.
        
        Args:
            nation_id: Nation ID
            recent_events: List of recent diplomatic events
            recent_actions: List of recent diplomatic actions
            
        Returns:
            Formatted input prompt (~2000 tokens max)
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # 1. Pending Proposals (require response)
        sections.append(self._build_pending_proposals(nation))
        
        # 2. Full Relationship Matrix
        sections.append(self._build_relationships(nation_id))
        
        # 3. Power Balance
        sections.append(self._build_power_balance(nation_id))
        
        # 4. Recent Diplomatic Events
        if recent_events:
            sections.append(self._build_events(recent_events))
        
        # 5. Recent Diplomatic Actions
        if recent_actions:
            sections.append(self._build_recent_actions(recent_actions))
        
        return "\n\n".join(sections)
    
    def _build_pending_proposals(self, nation: NationState) -> str:
        """Build pending proposals requiring response."""
        lines = ["## 📬 PENDING PROPOSALS (Require Response)"]
        
        if not nation.pending_proposals:
            lines.append("No pending proposals.")
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
            lines.append(f"  → Use ACCEPT_PROPOSAL or REJECT_PROPOSAL with target={from_nation}")
        
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
            
            # Trust description
            if trust_level >= 80:
                trust_desc = "Strong ally"
            elif trust_level >= 60:
                trust_desc = "Friendly"
            elif trust_level >= 40:
                trust_desc = "Neutral"
            elif trust_level >= 20:
                trust_desc = "Distrustful"
            else:
                trust_desc = "Hostile"
            
            entry = {
                "name": other_nation.name,
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
                lines.append(f"  - {e['name']}: Trust {e['trust']:.0f} ({e['trust_desc']})")
        
        if allies:
            lines.append("\n**🟢 ALLIES:**")
            for e in allies:
                lines.append(f"  - {e['name']}: Trust {e['trust']:.0f} ({e['trust_desc']})")
        
        if neutral:
            lines.append("\n**⚪ NEUTRAL/PEACE:**")
            for e in sorted(neutral, key=lambda x: -x['trust']):
                alliance_possible = "✅ Alliance possible" if e['trust'] >= 60 else ""
                lines.append(f"  - {e['name']}: Trust {e['trust']:.0f} ({e['trust_desc']}) {alliance_possible}")
        
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
