"""
Nation Info Panel Component.

Displays nation stats, resources, and spatial intelligence report.
"""

import streamlit as st
from geomas.schemas.world import WorldState
from geomas.world.spatial import SpatialTranslator


def render_nation_panel(world: WorldState, nation_id: str) -> None:
    """
    Renders the nation information panel with stats and intel.
    
    Args:
        world: Current world state
        nation_id: ID of the selected nation
    """
    nation = world.nations[nation_id]
    translator = SpatialTranslator(world)
    
    st.markdown(f"### {nation.name}")
    
    # Key metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Budget", f"{nation.total_budget:.0f}")
    c2.metric("Satisfaction", f"{nation.internal_state.public_satisfaction:.2f}")
    c3.metric("Population", f"{nation.total_population:,}")
    c4.metric("Power", f"{nation.power_projection:.1f}")
    
    # Resource bars
    st.progress(min(1.0, nation.total_food / 10000), text=f"Food: {nation.total_food:.0f}")
    st.progress(min(1.0, nation.total_energy / 5000), text=f"Energy: {nation.total_energy:.0f}")
    st.progress(min(1.0, nation.total_materials / 5000), text=f"Materials: {nation.total_materials:.0f}")
    
    # Intelligence report
    st.markdown("#### 🕵️‍♂️ Spatial Intelligence Report")
    report = translator.generate_intelligence_report(nation_id)
    st.markdown(report)


def render_nation_selector(world: WorldState) -> str:
    """
    Renders nation selection dropdown.
    
    Returns:
        Selected nation ID
    """
    nation_ids = list(world.nations.keys())
    
    if "nation_index" not in st.session_state:
        st.session_state["nation_index"] = 0
    
    def format_nation_option(nation_id):
        return world.nations[nation_id].name
    
    selected_nation_id = st.selectbox(
        "Select Nation",
        nation_ids,
        format_func=format_nation_option,
        index=st.session_state["nation_index"],
        key="nation_selector"
    )
    
    if selected_nation_id:
        st.session_state["nation_index"] = nation_ids.index(selected_nation_id)
    
    return selected_nation_id
