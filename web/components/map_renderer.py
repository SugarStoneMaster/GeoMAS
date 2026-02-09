"""
Map Rendering Component.

Handles the Voronoi map visualization with terrain colors.
"""

import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.colors as mcolors
from typing import Optional

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


def desaturate_color(hex_color: str, factor: float = 0.5) -> str:
    """Desaturate a color by blending with gray."""
    rgb = mcolors.hex2color(hex_color)
    gray = sum(rgb) / 3
    desaturated = [c * factor + gray * (1 - factor) for c in rgb]
    return mcolors.to_hex(desaturated)


def blend_with_ocean(nation_hex: str, ocean_hex: str = "#b0c4de", ratio: float = 0.35) -> str:
    """Blend nation color with ocean color for territorial waters."""
    nation_rgb = mcolors.hex2color(nation_hex)
    ocean_rgb = mcolors.hex2color(ocean_hex)
    blended = [nation_rgb[i] * ratio + ocean_rgb[i] * (1 - ratio) for i in range(3)]
    return mcolors.to_hex(blended)


def render_map(world: WorldState, selected_nation_id: Optional[str] = None, show_province_ids: bool = False) -> None:
    """
    Renders the world map as a matplotlib figure in Streamlit.
    
    Features:
        - Ocean provinces in steel blue
        - Territorial waters: blended nation color + ocean with wave pattern
        - Nation territories in their assigned colors
        - Mountains darkened with dotted pattern
        - Provinces in revolt marked with red X
        - Selected nation highlighted with bright border
    """
    # Build territorial water ownership lookup
    territorial_owners = {}
    for nation_id, nation in world.nations.items():
        for water_id in nation.territorial_water_ids:
            territorial_owners[water_id] = nation_id
    
    # Build province ownership for highlighting
    province_to_nation = {}
    for p_id, province in world.provinces.items():
        if province.owner_id:
            province_to_nation[p_id] = province.owner_id
        elif p_id in territorial_owners:
            province_to_nation[p_id] = territorial_owners[p_id]
    
    fig, ax = plt.subplots(figsize=(10, 8))
    patches = []
    colors = []
    hatches = []
    edge_colors = []
    edge_colors = []
    edge_widths = []
    revolt_coords = []  # Track provinces in civil unrest
    
    for p_id, province in world.provinces.items():
        if province.vertices:
            poly = Polygon(province.vertices)
            patches.append(poly)
            
            # Determine if this province belongs to selected nation
            belongs_to_selected = (province_to_nation.get(p_id) == selected_nation_id) if selected_nation_id else False
            
            if province.terrain == TerrainType.OCEAN:
                # Check if this ocean cell is territorial water
                owner_id = territorial_owners.get(p_id)
                if owner_id:
                    owner = world.nations.get(owner_id)
                    if owner:
                        # Blend nation color with ocean for territorial waters
                        blended = blend_with_ocean(owner.color)
                        if selected_nation_id and owner_id != selected_nation_id:
                            blended = desaturate_color(blended, 0.4)
                        colors.append(blended)
                        hatches.append("//")
                    else:
                        colors.append("#b0c4de")
                        hatches.append(None)
                else:
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
                    
                    # Desaturate non-selected nations
                    if selected_nation_id and province.owner_id != selected_nation_id:
                        final_color = desaturate_color(final_color, 0.4)
                    
                    colors.append(final_color)
                    
                    # Mark provinces in revolt
                    if province.in_revolt:
                        revolt_coords.append((province.coordinates[0], province.coordinates[1]))
                else:
                    colors.append("#808080")
                    hatches.append(None)
            
            # Highlight selected nation with bright border
            if belongs_to_selected:
                edge_colors.append("#FFD700")  # Gold border
                edge_widths.append(1.5)
            else:
                edge_colors.append("black")
                edge_widths.append(0.2)
    
    if patches:
        # Draw each patch individually to support different edge colors
        for i, patch in enumerate(patches):
            patch.set_facecolor(colors[i])
            patch.set_edgecolor(edge_colors[i])
            patch.set_linewidth(edge_widths[i])
            patch.set_hatch(hatches[i])
            ax.add_patch(patch)
            
    # Draw a subtle border for the world box (0,1)
    world_box = plt.Rectangle((0, 0), 1, 1, fill=False, edgecolor='gray', linestyle='--', alpha=0.5, linewidth=0.5)
    ax.add_patch(world_box)
            
    # Render Province IDs if requested
    if show_province_ids:
        for p_id, province in world.provinces.items():
            if province.coordinates:
                cx, cy = province.coordinates
                
                ax.text(
                    cx, cy, 
                    str(p_id), 
                    fontsize=6, 
                    ha='center', 
                    va='center', 
                    color='black',
                    clip_on=True, # Ensure it doesn't expand axes or show outside
                    bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', boxstyle='round,pad=0.1')
                )
    
    
    # Draw revolt markers (red X) on provinces in civil unrest
    for rx, ry in revolt_coords:
        ax.scatter(rx, ry, s=80, c='red', marker='X', edgecolors='darkred', linewidths=1, zorder=11)
    
    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.1, 1.1)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Minimize white space around the plot
    fig.tight_layout(pad=0)
    
    st.pyplot(fig)
    plt.close(fig)

