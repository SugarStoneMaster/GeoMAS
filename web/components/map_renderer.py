"""
Map Rendering Component.

Handles the Voronoi map visualization with terrain colors and capitals.
"""

import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.colors as mcolors

from geomas.schemas.world import WorldState, TerrainType


def darken_color(hex_color: str, factor: float = 0.7) -> str:
    """Darken a hex color by a factor (0-1)."""
    rgb = mcolors.hex2color(hex_color)
    darker_rgb = [max(0, c * factor) for c in rgb]
    return mcolors.to_hex(darker_rgb)


def render_map(world: WorldState) -> None:
    """
    Renders the world map as a matplotlib figure in Streamlit.
    
    Features:
        - Ocean provinces in steel blue
        - Nation territories in their assigned colors
        - Mountains darkened with dotted pattern
        - Capital provinces marked with gold stars
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    patches = []
    colors = []
    hatches = []
    capital_coords = []
    
    for p_id, province in world.provinces.items():
        if province.vertices:
            poly = Polygon(province.vertices)
            patches.append(poly)
            
            if province.terrain == TerrainType.OCEAN:
                colors.append("#b0c4de")
                hatches.append(None)
            else:
                owner = world.nations.get(province.owner_id)
                if owner:
                    base_color = owner.color
                    if province.terrain == TerrainType.MOUNTAIN:
                        final_color = darken_color(base_color, factor=0.6)
                        hatches.append("...")
                    else:
                        final_color = base_color
                        hatches.append(None)
                    colors.append(final_color)
                    
                    # Mark capital
                    if owner.capital_province_id == p_id:
                        capital_coords.append((province.coordinates[0], province.coordinates[1], "gold"))
                else:
                    colors.append("#808080")
                    hatches.append(None)
    
    if patches:
        p = PatchCollection(patches, match_original=True)
        p.set_facecolor(colors)
        p.set_edgecolor('black')
        p.set_linewidth(0.2)
        for i, patch in enumerate(patches):
            patch.set_hatch(hatches[i])
        ax.add_collection(p)
    
    # Draw capital stars
    for cx, cy, ccolor in capital_coords:
        ax.scatter(cx, cy, s=120, c=ccolor, marker='*', edgecolors='black', zorder=10)
    
    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.1, 1.1)
    ax.set_aspect('equal')
    ax.axis('off')
    
    st.pyplot(fig)
    plt.close(fig)
