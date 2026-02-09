"""
Map & Intel Page.

Displays the world map with nation stats and intelligence panel.
Layout: Stats (left) | Map + Trust Matrix (center) | Intel Report (right)
"""

import streamlit as st
from geomas.schemas.world import WorldState
from geomas.agents.context import SpatialTranslator

from web.components.map_renderer import render_map
from web.components.nation_panel import render_nation_stats
from web.components.trust_matrix import render_trust_matrix
from web.components.inspector import render_inspector
import streamlit as st


def render_map_page(world: WorldState) -> None:
    """Renders the Map & Intel tab content with 3-column layout."""
    
    # Nation selector at top
    selected_nation_id = render_nation_selector(world)
    
    st.divider()
    
    # 3-column layout: Stats | Map + Trust | Intel
    col_stats, col_map, col_intel = st.columns([1, 2, 1])
    
    with col_stats:
        st.markdown("### 📊 Stats")
        if selected_nation_id:
            render_nation_stats(world, selected_nation_id)
    
    with col_map:
        show_ids = st.checkbox("Show Province IDs", value=False, key="map_show_ids")
        render_map(world, selected_nation_id, show_province_ids=show_ids)
        # Trust matrix directly under the map
        render_trust_matrix(world)
    
    with col_intel:
        st.markdown("### 🕵️ Intel")
        if selected_nation_id:
            translator = SpatialTranslator(world)
            report = translator.generate_intelligence_report(selected_nation_id)
            st.markdown(report)
            
            st.divider()
            
            # INSPECTOR PANEL
            if "sim" in st.session_state and st.session_state["sim"]:
                sim = st.session_state["sim"]
                if selected_nation_id in sim.agents:
                    agent = sim.agents[selected_nation_id]
                    trace = getattr(agent, 'last_trace', {})
                    render_inspector(selected_nation_id, trace)


def render_nation_selector(world: WorldState) -> str:
    """Renders nation selection dropdown."""
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
