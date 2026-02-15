"""
Economy Minister Input Builder.

Generates dynamic context for the Economy Minister agent.
Includes full economic state, satisfaction, and trade opportunities.
"""

from typing import Optional, List, Dict, Any
from geomas.schemas.world import WorldState, NationState


class EconomyInputBuilder:
    """
    Builds dynamic input context for the Economy Minister agent.
    
    The Economy Minister receives:
    - Full economic state (budget, resources, production)
    - Public satisfaction (can affect it directly)
    - Pending trade offers
    - Resource analysis (surplus/shortage)
    - Recent economic actions
    """
    
    def __init__(self, world: WorldState):
        self.world = world
    
    def build(
        self,
        nation_id: str,
        turn: int,
        pending_trades: Optional[List[Dict[str, Any]]] = None,
        recent_actions: Optional[List[str]] = None,
        context_manager: Optional['ContextManager'] = None,
    ) -> str:
        """
        Build the input context for the Economy Minister.
        
        Args:
            nation_id: Nation ID
            turn: Current turn number
            pending_trades: List of pending trade offers
            recent_actions: List of recent economic actions (legacy)
            context_manager: Optional ContextManager for rich history
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
            feedback = context_manager.get_presidential_feedback(nation_id, "Economy")
            if feedback:
                sections.append(feedback)
            
            sections.append(self._build_world_events(nation_id, context_manager))
            sections.append(self._build_self_history(nation_id, context_manager))
        
        # 3. Feedback from Previous Turn (Clamped)
        clamped_action = next((a for a in (recent_actions or []) if "Clamped" in a), None)
        if clamped_action:
            sections.append(f"## Feedback from previous turn\n**Your last trade was AUTOMATICALLY REDUCED because it exceeded 15% of reserves/capacity.**\n- Log: \"{clamped_action}\"\n- **Correction:** Please offer smaller amounts (max 15% of surplus) to avoid this.\n")
        
        # 4. Treasury (All Resources)
        sections.append(self._build_treasury_section(nation))
        
        # 5. Resource Production
        sections.append(self._build_resources_section(nation_id))
        
        # 6. Public Satisfaction
        sections.append(self._build_satisfaction_section(nation))
        
        # 7. Pending Trade Offers
        if pending_trades:
            sections.append(self._build_trades_section(pending_trades))
        
        # 8. Global Market Intelligence
        sections.append(self._build_global_market(nation_id))
        
        return "\n\n".join(sections)
    
    def _build_treasury_section(self, nation: NationState) -> str:
        """Build treasury section with all resources."""
        # Calculate income (simplified - from tax revenue)
        income = sum(
            self.world.provinces[p_id].tax_revenue 
            for p_id in nation.province_ids
            if p_id in self.world.provinces
        )
        
        # Budget health
        if nation.total_budget > 5000:
            status = "WEALTHY"
        elif nation.total_budget > 1000:
            status = "STABLE"
        elif nation.total_budget > 100:
            status = "TIGHT"
        else:
            status = "CRITICAL"
        
        return f"""## Treasury
**Treasury Status:** {status}
- **Budget:** {nation.total_budget:,.0f} (Estimated Income: {income:,.0f}/turn)
- **Food:** {nation.total_food:,.0f}
- **Energy:** {nation.total_energy:,.0f}
- **Materials:** {nation.total_materials:,.0f}
"""

    def _build_resources_section(self, nation_id: str) -> str:
        """Build resource production section."""
        nation = self.world.nations[nation_id]
        
        # Analyze each resource
        resources = {
            "Food": nation.total_food,
            "Energy": nation.total_energy,
            "Materials": nation.total_materials
        }
        
        lines = ["## Resource production"]
        
        shortages = []
        surpluses = []
        
        for name, value in resources.items():
            if value < 50:
                status = "⚠️ SHORTAGE"
                shortages.append(name.lower())
            elif value > 500:
                status = "✅ SURPLUS"
                surpluses.append(name.lower())
            else:
                status = "→ ADEQUATE"
            
            lines.append(f"- **{name}:** {value:+.0f}/turn {status}")
        
        if shortages:
            lines.append(f"\n**Trade Priority:** Need {', '.join(shortages)}")
        if surpluses:
            lines.append(f"**Trade Offer:** Can export {', '.join(surpluses)} (Max export per trade: 15% of stock)")
        
        return "\n".join(lines)
    
    def _build_satisfaction_section(self, nation: NationState) -> str:
        """Build satisfaction section (Economy can affect it)."""
        sat = nation.public_satisfaction
        
        # Status and recommendations
        if sat < 20:
            status = "⚠️ CRISIS"
            recommendation = "URGENT: Use INVEST_IN_WELFARE immediately. Avoid WAR_TAX."
        elif sat < 30:
            status = "⚠️ DANGEROUSLY LOW"
            recommendation = "Consider INVEST_IN_WELFARE. WAR_TAX not possible."
        elif sat < 50:
            status = "⚠️ BELOW OPTIMAL"
            recommendation = "INVEST_IN_WELFARE recommended if budget allows."
        elif sat < 70:
            status = "✅ STABLE"
            recommendation = "Population is content. WAR_TAX possible if needed."
        else:
            status = "✅ HIGH"
            recommendation = "Excellent morale. War operations well-tolerated."
        
        return f"""## Public satisfaction
**Current:** {sat:.0f}% {status}

{recommendation}"""

    def _build_trades_section(self, pending_trades: List[Dict[str, Any]]) -> str:
        """Build pending trade offers section."""
        lines = ["## Pending trade offers"]
        
        for trade in pending_trades:
            from_nation = trade.get("from", "Unknown")
            offer = trade.get("offer", {})
            request = trade.get("request", {})
            
            lines.append(f"\n**From {from_nation}:**")
            lines.append(f"  They offer: {offer}")
            lines.append(f"  They want: {request}")
        
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
            
            # TRADE ELIGIBILITY TAG
            trade_tag = "[TRADE ELIGIBLE]" if trust_val >= 40 and rel != "WAR" else "[NO TRADE - Trust too low or War]"
            
            line = f"- **{other_nation.name}** ({other_id}): {rel}, Trust {trust_val:.0f} {trade_tag}"
            
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

    def _build_self_history(self, nation_id: str, cm: 'ContextManager') -> str:
        """Build domain-specific history for Economy Minister."""
        from geomas.agents.context.events.schemas import EventType
        
        lines = ["## Your history"]
        
        # 1. Economy Actions
        action_lines = cm.get_actions_for(nation_id, domain="Economy", max_actions=8)
        
        # 2. Economy-related Events
        economy_event_types = [
            EventType.TRADE_DEAL,
            EventType.ECONOMIC_CRISIS,
            EventType.CIVIL_UNREST
        ]
        event_lines = cm.get_events_for(nation_id, max_events=8, event_types=economy_event_types)
        
        if action_lines:
            lines.append("### Recent Actions")
            lines.extend([f"- {a}" for a in action_lines])
            
        if event_lines:
            lines.append("### Notable Economic Events")
            lines.extend([f"- {e}" for e in event_lines])
            
        if not action_lines and not event_lines:
            lines.append("- No recent economic history.")
            
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

    def _build_global_market(self, nation_id: str) -> str:
        """Build global market intelligence with dynamic thresholds."""
        nations = [n for nid, n in self.world.nations.items() if nid != nation_id]
        if not nations:
            return "## 🌍 GLOBAL MARKET INTELLIGENCE\nNo other nations found."

        # 1. Calculate Global Averages
        total_food = sum(n.total_food for n in nations)
        total_energy = sum(n.total_energy for n in nations)
        total_materials = sum(n.total_materials for n in nations)
        count = len(nations)
        
        avg_food = total_food / count if count > 0 else 0
        avg_energy = total_energy / count if count > 0 else 0
        avg_materials = total_materials / count if count > 0 else 0
        
        lines = ["## Global market intelligence"]
        lines.append(f"Global Averages: Food {avg_food:.0f}, Energy {avg_energy:.0f}, Materials {avg_materials:.0f}.")
        lines.append("- **SURPLUS**: > 120% of Avg. Ask them for this!")
        lines.append("- **DEFICIT**: < 80% of Avg. Sell this to them!")
        lines.append("⚠️ **IMPORTANT**: Trades are CAPPED at 15% of the source nation's current stock. Requests > 15% will be automatically CLAMPED. Ask for CONSERVATIVE amounts (<15% of surplus) to ensure full value.")
        
        has_data = False
        
        for other in nations:
            surpluses = []
            deficits = []
            
            # Dynamic Thresholds
            if other.total_food > avg_food * 1.2: surpluses.append("FOOD")
            elif other.total_food < avg_food * 0.8: deficits.append("food")
            
            if other.total_energy > avg_energy * 1.2: surpluses.append("ENERGY")
            elif other.total_energy < avg_energy * 0.8: deficits.append("energy")
            
            if other.total_materials > avg_materials * 1.2: surpluses.append("MATERIALS")
            elif other.total_materials < avg_materials * 0.8: deficits.append("materials")
            
            if surpluses or deficits:
                has_data = True
                
                # Trust and Eligibility check
                trust_val = self.world.trust_matrix.get(nation_id, {}).get(other.id, 50.0)
                rel = self.world.relationship_matrix.get(nation_id, {}).get(other.id, "PEACE")
                is_eligible = trust_val >= 40 and rel != "WAR"
                eligibility_tag = "✅ [TRADE ELIGIBLE]" if is_eligible else "❌ [NO TRADE - Trust too low or War]"
                
                info = f"- **{other.name} ({other.id})** {eligibility_tag}:"
                if surpluses:
                    info += f" HAS {', '.join(surpluses)}"
                if deficits:
                    info += f" NEEDS {', '.join(deficits)}"
                lines.append(info)
        
        if not has_data:
            lines.append("No significant market imbalances detected (everyone is near average).")
            
        return "\n".join(lines)

