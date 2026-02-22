"""
Nation Stats Component.

Displays nation stats in a compact format for the sidebar panel.
"""

from typing import Any
import streamlit as st
from geomas.schemas.world import WorldState


def format_number(n: float, decimals: int = 0) -> str:
    """Format number with Italian locale (dots as thousand separators)."""
    if decimals == 0:
        formatted = f"{int(n):,}".replace(",", ".")
    else:
        formatted = f"{n:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def render_nation_stats(world: WorldState, nation_id: str, agent: Any = None) -> None:
    """
    Renders compact nation stats for 3-column layout.
    
    Args:
        world: Current world state
        nation_id: ID of the selected nation
        agent: Optional agent object to extract strategy
    """
    nation = world.nations[nation_id]
    
    st.markdown(f"### **{nation.name}**")
    
    # Strategy and Government Info
    gov_type = nation.government_type or "UNKNOWN"
    strategy = agent.strategy.value if agent and hasattr(agent, 'strategy') else "UNKNOWN"
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.caption("🏛️ Government")
        st.markdown(f"**{gov_type}**")
    with col_info2:
        st.caption("🎯 Strategy")
        st.markdown(f"**{strategy}**")
        
    st.divider()
    
    # Overview metrics
    st.metric("💰 Budget", format_number(nation.total_budget))
    st.metric("😊 Satisfaction", f"{nation.public_satisfaction:.0f}/100")
    st.metric("⚡ Power", format_number(nation.power_projection, 1))
    
    st.markdown("---")
    
    # Population - bigger emphasis
    st.markdown("##### 👥 Population")
    st.markdown(f"**{format_number(nation.total_population)}** total")
    st.markdown(f"{format_number(nation.total_workers)} workers")
    
    st.markdown("---")
    
    # Resources - BIGGER and more prominent
    st.markdown("##### 🌾 Resources")
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.metric("🍞 Food", format_number(nation.total_food))
        st.metric("🔧 Materials", format_number(nation.total_materials))
    with res_col2:
        st.metric("⚡ Energy", format_number(nation.total_energy))
    
    st.markdown("---")
    
    # Military
    st.markdown("##### ⚔️ Military")
    mil_col1, mil_col2 = st.columns(2)
    with mil_col1:
        st.markdown(f"🎖️ {format_number(nation.total_soldiers)}")
        st.markdown(f"🚢 {format_number(nation.total_navy)}")
    with mil_col2:
        st.markdown(f"✈️ {format_number(nation.total_aircraft)}")
        st.markdown(f"☢️ {nation.nukes}")
