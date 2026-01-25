"""
Trust Matrix Component.

Displays the diplomatic trust matrix as a styled dataframe.
"""

import streamlit as st
import pandas as pd
from geomas.schemas.world import WorldState


def render_trust_matrix(world: WorldState) -> None:
    """
    Renders the trust matrix as a color-coded dataframe.
    
    Green = high trust, Red = low trust.
    """
    st.subheader("🤝 Diplomatic Trust Matrix")
    
    df_trust = pd.DataFrame(world.trust_matrix)
    # Sort for consistency
    df_trust = df_trust.sort_index().sort_index(axis=1)
    
    st.dataframe(
        df_trust.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=1),
        use_container_width=True
    )
