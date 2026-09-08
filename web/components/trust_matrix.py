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
    
    Scale: 0-100 (Green = high trust, Red = low trust).
    """
    st.subheader("🤝 Diplomatic Trust Matrix")
    st.caption("Asymmetric Scale 0-100: How much the **Column** nation trusts the **Row** nation.")
    
    df_trust = pd.DataFrame(world.trust_matrix)
    # pd.DataFrame(dict_of_dicts) makes outer keys (Observer) columns and inner keys (Target) rows.
    df_trust.index.name = "Target ↓"
    df_trust.columns.name = "Observer →"
    
    # Sort for consistency
    df_trust = df_trust.sort_index().sort_index(axis=1)
    
    # Convert to integer for cleaner display, filling any NaN with neutral 50
    df_trust = df_trust.fillna(50).astype(int)
    
    st.dataframe(
        df_trust.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=100),
        width="stretch"
    )

