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


def lighten_color(hex_color: str, factor: float = 0.5) -> str:
    """Lighten a hex color by blending with white."""
    rgb = mcolors.hex2color(hex_color)
    lighter_rgb = [min(1.0, c + (1.0 - c) * factor) for c in rgb]
    return mcolors.to_hex(lighter_rgb)


def blend_with_ocean(nation_hex: str, ocean_hex: str = "#b0c4de", ratio: float = 0.35) -> str:
    """Blend nation color with ocean color for territorial waters."""
    nation_rgb = mcolors.hex2color(nation_hex)
    ocean_rgb = mcolors.hex2color(ocean_hex)
    blended = [nation_rgb[i] * ratio + ocean_rgb[i] * (1 - ratio) for i in range(3)]
    return mcolors.to_hex(blended)


def render_map(world: WorldState) -> None:
    """
    Renders the world map as a matplotlib figure in Streamlit.
    
    Features:
        - Ocean provinces in steel blue
        - Territorial waters: blended nation color + ocean with wave pattern
        - Nation territories in their assigned colors
        - Mountains darkened with dotted pattern
        - Capital provinces marked with gold stars
    """
    # Build territorial water ownership lookup
    territorial_owners = {}
    for nation_id, nation in world.nations.items():
        for water_id in nation.territorial_water_ids:
            territorial_owners[water_id] = nation_id
    
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
                # Check if this ocean cell is territorial water
                owner_id = territorial_owners.get(p_id)
                if owner_id:
                    owner = world.nations.get(owner_id)
                    if owner:
                        # Blend nation color with ocean for territorial waters
                        blended = blend_with_ocean(owner.color)
                        colors.append(blended)
                        hatches.append("//")  # Diagonal stripes for territorial waters
                    else:
                        colors.append("#b0c4de")
                        hatches.append(None)
                else:
                    # Regular ocean (international waters)
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
