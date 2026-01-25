"""
Map & Intel Page.

Displays the world map and nation intelligence panel.
"""

import streamlit as st
from geomas.schemas.world import WorldState

from web.components.map_renderer import render_map
from web.components.nation_panel import render_nation_panel, render_nation_selector
from web.components.trust_matrix import render_trust_matrix


def render_map_page(world: WorldState) -> None:
    """Renders the Map & Intel tab content."""
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        render_map(world)
    
    with col2:
        selected_nation_id = render_nation_selector(world)
        if selected_nation_id:
            render_nation_panel(world, selected_nation_id)
    
    # Trust matrix below the map
    st.divider()
    render_trust_matrix(world)
