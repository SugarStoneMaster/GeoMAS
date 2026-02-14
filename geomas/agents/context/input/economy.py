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
    ) -> str:
        """
        Build the input context for the Economy Minister.
        
        Args:
            nation_id: Nation ID
            pending_trades: List of pending trade offers
            recent_actions: List of recent economic actions
            
        Returns:
            Formatted input prompt (~1500 tokens max)
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # Metadata Header for Observability
        sections.append(f"## TURN {turn}")

        # 0. FEEDBACK WARNING (If previous trade was clamped)
        # Scan recent actions for "Clamped" keyword (covers both Sender and Receiver limits)
        clamped_action = next((a for a in (recent_actions or []) if "Clamped" in a), None)
        if clamped_action:
            # Extract details if possible or just warn
            sections.append(f"""## ⚠️ FEEDBACK FROM PREVIOUS TURN
**Your last trade was AUTOMATICALLY REDUCED because it exceeded 15% of reserves/capacity.**
- Log: "{clamped_action}"
- **Correction:** Please offer smaller amounts (max 15% of surplus) to avoid this.
""")
        
        # 1. Treasury and Budget
        sections.append(self._build_treasury_section(nation))
        
        # 2. Resource Production
        sections.append(self._build_resources_section(nation_id))
        
        # 3. Public Satisfaction (Economy can affect it)
        sections.append(self._build_satisfaction_section(nation))
        
        # 4. Pending Trade Offers
        if pending_trades:
            sections.append(self._build_trades_section(pending_trades))
        
        # 5. Trade Partners Status
        sections.append(self._build_trade_partners(nation_id))
        
        # 6. Global Market Intelligence (NEW)
        sections.append(self._build_global_market(nation_id))
        
        # 7. Recent Economic Actions
        if recent_actions:
            sections.append(self._build_recent_actions(recent_actions))
        
        return "\n\n".join(sections)
    
    def _build_treasury_section(self, nation: NationState) -> str:
        """Build treasury and budget section."""
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
        
        return f"""## 💰 TREASURY
**Current Budget:** {nation.total_budget:,.0f} ({status})
**Estimated Income:** {income:,.0f}/turn (from taxes)

**Key Costs:**
- INVEST_WELFARE: Cost is **Budget + Materials** (Materials = 20% of Budget amount).
  * Example: 500 Budget investment requires 500 Budget AND 100 Materials.
  * Gain: ~5 satisfaction (logarithmic).
- RAISE_WAR_TAX: +budget (0.01 × Population), -15 satisfaction"""

    def _build_resources_section(self, nation_id: str) -> str:
        """Build resource production section."""
        nation = self.world.nations[nation_id]
        
        # Analyze each resource
        resources = {
            "Food": nation.total_food,
            "Energy": nation.total_energy,
            "Materials": nation.total_materials
        }
        
        lines = ["## 📊 RESOURCE PRODUCTION"]
        
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
        
        return f"""## 👥 PUBLIC SATISFACTION
**Current:** {sat:.0f}% {status}

{recommendation}

**Your Tools:**
- `INVEST_WELFARE`: Spend budget → satisfaction boost (logarithmic: 7*log(1+amount/500))
- `RAISE_WAR_TAX`: +budget, -15 satisfaction (requires satisfaction > 30)"""

    def _build_trades_section(self, pending_trades: List[Dict[str, Any]]) -> str:
        """Build pending trade offers section."""
        lines = ["## 📬 PENDING TRADE OFFERS"]
        
        for trade in pending_trades:
            from_nation = trade.get("from", "Unknown")
            offer = trade.get("offer", {})
            request = trade.get("request", {})
            
            lines.append(f"\n**From {from_nation}:**")
            lines.append(f"  They offer: {offer}")
            lines.append(f"  They want: {request}")
        
        return "\n".join(lines)
    
    def _build_trade_partners(self, nation_id: str) -> str:
        """Build potential trade partners status."""
        lines = ["## 🤝 TRADE PARTNERS"]
        
        if nation_id not in self.world.relationship_matrix:
            lines.append("No established relationships.")
            return "\n".join(lines)
        
        relationships = self.world.relationship_matrix[nation_id]
        trust = self.world.trust_matrix.get(nation_id, {})
        
        for other_id, status in relationships.items():
            # Skip nations that were filtered out
            if other_id not in self.world.nations:
                continue
            other = self.world.nations[other_id]
            trust_level = trust.get(other_id, 50)
            
            if status == "WAR":
                trade_status = "❌ Cannot trade (at war)"
            elif trust_level < 40:
                trade_status = "❌ Cannot trade (trust < 40)"
            elif status == "ALLIANCE":
                trade_status = "✅ Preferred partner"
            elif trust_level >= 50:
                trade_status = "✅ Trade possible"
            else:
                trade_status = "⚠️ Trade possible but low trust"
            
            lines.append(f"- **{other_id}**: {status}, Trust {trust_level:.0f} - {trade_status}")
        
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
        
        lines = ["## 🌍 GLOBAL MARKET INTELLIGENCE"]
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
                info = f"- **{other.name} ({other.id})**:"
                if surpluses:
                    info += f" HAS {', '.join(surpluses)}"
                if deficits:
                    info += f" NEEDS {', '.join(deficits)}"
                lines.append(info)
        
        if not has_data:
            lines.append("No significant market imbalances detected (everyone is near average).")
            
        return "\n".join(lines)

    def _build_recent_actions(self, actions: List[str]) -> str:
        """Build recent economic actions section."""
        lines = ["## 📋 RECENT ECONOMIC ACTIONS"]
        for action in actions[-5:]:
            lines.append(f"- {action}")
        return "\n".join(lines)
