"""
Nation Stats Component.

Displays nation stats in a compact format for the sidebar panel.
"""

import streamlit as st
from geomas.schemas.world import WorldState


def format_number(n: float, decimals: int = 0) -> str:
    """Format number with Italian locale (dots as thousand separators)."""
    if decimals == 0:
        formatted = f"{int(n):,}".replace(",", ".")
    else:
        formatted = f"{n:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def render_nation_stats(world: WorldState, nation_id: str) -> None:
    """
    Renders compact nation stats for 3-column layout.
    
    Args:
        world: Current world state
        nation_id: ID of the selected nation
    """
    nation = world.nations[nation_id]
    
    st.markdown(f"**{nation.name}**")
    
    # Overview metrics
    st.metric("💰 Budget", format_number(nation.total_budget))
    st.metric("😊 Satisfaction", f"{nation.public_satisfaction:.0%}")
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
