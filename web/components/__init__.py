"""
Web Components Package.

Reusable UI components for the Streamlit dashboard.
"""

from web.components.map_renderer import render_map, darken_color
from web.components.nation_panel import render_nation_stats
from web.components.trust_matrix import render_trust_matrix

__all__ = [
    "render_map",
    "darken_color",
    "render_nation_stats",
    "render_trust_matrix"
]
