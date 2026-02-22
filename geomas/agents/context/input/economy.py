"""
Economy Minister Input Builder.

Generates dynamic context for the Economy Minister agent.
Includes full economic state, satisfaction, and trade opportunities.
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from geomas.schemas.world import NationState
from geomas.agents.context.input.base import BaseInputBuilder

if TYPE_CHECKING:
    from geomas.agents.context.events import ContextManager


class EconomyInputBuilder(BaseInputBuilder):
    """
    Builds dynamic input context for the Economy Minister agent.
    
    The Economy Minister receives:
    - Full economic state (budget, resources, production)
    - Public satisfaction (can affect it directly)
    - Pending trade offers
    - Resource analysis (surplus/shortage)
    - Recent economic actions
    """
    
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
        sections.append(self._build_month_header(turn))
        
        # 2. Common Layers
        sections.append(self._build_relationships(nation_id))
        sections.append(self._build_other_nations(nation_id))
        
        if context_manager:
            feedback = self._build_presidential_feedback(nation_id, "Economy", context_manager)
            if feedback:
                sections.append(feedback)
            
            sections.append(self._build_world_events(nation_id, context_manager))
            sections.append(self._build_self_history(nation_id, context_manager, domain="Economy"))
        
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

        # 7. INVEST_WELFARE cost table (concrete amounts & feasibility)
        sections.append(self._build_welfare_cost_preview(nation))

        # 8. Pending Trade Offers
        if pending_trades:
            sections.append(self._build_trades_section(pending_trades))

        # 9. Global Market Intelligence
        sections.append(self._build_global_market(nation_id))
        
        return self._sanitize_prompt("\n\n".join(sections))
    
    def _build_treasury_section(self, nation: NationState) -> str:
        """Build treasury section with all resources."""
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

        # War Impact
        war_lines = []
        if nation.active_wars:
            total_lost = sum(w.lost_provinces for w in nation.active_wars.values())
            if total_lost > 0:
                war_lines.append(f"\n**WAR IMPACT:**")
                war_lines.append(f"- Lost {total_lost} tax-paying provinces.")

        war_section = "\n".join(war_lines)

        return f"""## Treasury
> **Note:** Defense and Economy ministers plan concurrently from the same resource snapshot.
> If Defense recruits or moves units this turn, budget and materials will decrease before Economy executes.

**Treasury Status:** {status}
- **Budget:** {nation.total_budget:,.0f} (Estimated income: {income:,.0f}/turn)
- **Food:** {nation.total_food:,.0f}
- **Energy:** {nation.total_energy:,.0f}
- **Materials:** {nation.total_materials:,.0f}{war_section}
"""

    def _build_resources_section(self, nation_id: str) -> str:
        """Build resource production section."""
        nation = self.world.nations[nation_id]

        resources = {
            "Food": nation.total_food,
            "Energy": nation.total_energy,
            "Materials": nation.total_materials
        }

        lines = ["## Resource stockpiles"]

        for name, value in resources.items():
            if value < 50:
                status = "LOW"
            elif value > 500:
                status = "HIGH"
            else:
                status = "ADEQUATE"

            lines.append(f"- **{name}:** {value:,.0f} ({status})")

        return "\n".join(lines)
    
    def _build_welfare_cost_preview(self, nation: NationState) -> str:
        """
        Show concrete cost/benefit table for INVEST_WELFARE.
        Uses the same constants as handler.py to ensure accuracy.
        """
        import math
        # Constants mirrored from handler.py
        WELFARE_MATERIALS_RATIO = 0.2
        WELFARE_MAX_BUDGET_RATIO = 0.25
        WELFARE_LOG_CONSTANT = 500
        WELFARE_MULTIPLIER = 7

        max_affordable = nation.total_budget * WELFARE_MAX_BUDGET_RATIO
        max_materials = nation.total_materials

        def row(amount: float) -> str:
            mat = amount * WELFARE_MATERIALS_RATIO
            if amount > max_affordable or mat > max_materials:
                feasible = "❌ cannot afford"
            else:
                feasible = "✓ feasible"
            sat = WELFARE_MULTIPLIER * math.log(1 + amount / WELFARE_LOG_CONSTANT) if amount > 0 else 0
            return f"  amount={amount:.0f}: costs {amount:.0f} budget + {mat:.0f} materials → satisfaction +{sat:.1f} — {feasible}"

        # Show 3 representative amounts
        amounts = [100, 500, max_affordable] if max_affordable > 100 else [max_affordable]
        amounts = sorted(set(int(a) for a in amounts if a > 0))

        lines = ["## INVEST_WELFARE cost preview (budget + 20% materials per unit)"]
        lines.append(f"  Ceiling: {max_affordable:.0f} budget (25% of treasury) | Materials available: {max_materials:.0f}")
        for a in amounts:
            lines.append(row(a))
        return "\n".join(lines)

    def _build_satisfaction_section(self, nation: NationState) -> str:
        """Report public satisfaction and available economic actions with factual effects."""
        sat = nation.public_satisfaction

        if sat < 20:
            status = "CRITICALLY LOW"
        elif sat < 30:
            status = "LOW"
        elif sat < 50:
            status = "BELOW AVERAGE"
        elif sat < 70:
            status = "STABLE"
        else:
            status = "HIGH"

        return f"""## Public satisfaction
**Current:** {sat:.0f}% — {status}

**Available actions and their effects:**
- **INVEST_WELFARE**: increases satisfaction (logarithmic returns). Costs budget + 20% materials. See cost preview below.
- **RAISE_WAR_TAX**: increases budget by ~1% of population. Decreases satisfaction by 15 points (×1.5 if satisfaction < 30). Requires satisfaction ≥ 30.
- **TRADE_PROPOSAL**: exchanges resources with another nation. No direct satisfaction effect.
- **IDLE**: no economic action this turn."""

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

    def _build_global_market(self, nation_id: str) -> str:
        """Build global market intelligence with dynamic thresholds."""
        nations = [n for nid, n in self.world.nations.items() if nid != nation_id]
        if not nations:
            return "## GLOBAL MARKET INTELLIGENCE\nNo other nations found."

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
        lines.append("**IMPORTANT**: Trades are CAPPED at 15% of the source nation's current stock. Requests > 15% will be automatically CLAMPED. Ask for CONSERVATIVE amounts (<15% of surplus) to ensure full value.")
        
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
                eligibility_tag = "[TRADE ELIGIBLE]" if is_eligible else "[NO TRADE - Trust too low or War]"
                
                info = f"- **{other.name} ({other.id})** {eligibility_tag}:"
                if surpluses:
                    info += f" HAS {', '.join(surpluses)}"
                if deficits:
                    info += f" NEEDS {', '.join(deficits)}"
                lines.append(info)
        
        if not has_data:
            lines.append("No significant market imbalances detected (everyone is near average).")
            
        return "\n".join(lines)

