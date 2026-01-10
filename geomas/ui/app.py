import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Patch
from matplotlib.collections import PatchCollection
import matplotlib.colors as mcolors
import numpy as np
import sys
import os

# --- PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import Core Modules
from geomas.world.map_engine import generate_world
from geomas.schemas.models import WorldState, TerrainType
from geomas.world.spatial_translator import SpatialTranslator

st.set_page_config(page_title="GeoMAS Dashboard", layout="wide")

st.title("👑 GeoMAS: World Engine Inspector")

# --- SIDEBAR CONFIG ---
st.sidebar.header("World Generation Parameters")
map_seed = st.sidebar.number_input("Map Seed (Geometry)", value=42, step=1)
history_seed = st.sidebar.number_input("History Seed (Genesis)", value=99, step=1)

n_nations = 10 
st.sidebar.info(f"Simulation fixed to {n_nations} Preset Nations")
n_cells = st.sidebar.slider("Map Resolution (Cells)", 500, 3000, 1500)

# --- GENERATION LOGIC ---
@st.cache_data
def get_world(map_seed, history_seed, n_cells, n_nations):
    return generate_world(seed=map_seed, history_seed=history_seed, n_cells=n_cells, n_nations=n_nations)

if st.sidebar.button("Generate World"):
    st.session_state["world"] = get_world(map_seed, history_seed, n_cells, n_nations)
    st.success(f"World Generated with Map Seed {map_seed} & History Seed {history_seed}")

if "world" not in st.session_state:
    st.session_state["world"] = get_world(map_seed, history_seed, n_cells, n_nations)

world: WorldState = st.session_state["world"]
translator = SpatialTranslator(world)

# --- VISUALIZATION ---
col1, col2 = st.columns([3, 2])

def darken_color(hex_color, factor=0.7):
    """Darkens a hex color by a factor (0.0 to 1.0)."""
    rgb = mcolors.hex2color(hex_color)
    darker_rgb = [max(0, c * factor) for c in rgb]
    return mcolors.to_hex(darker_rgb)

with col1:
    st.subheader("Geopolitical Map")
    
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
    
    for cx, cy, ccolor in capital_coords:
        ax.scatter(cx, cy, s=120, c=ccolor, marker='*', edgecolors='black', zorder=10)

    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.1, 1.1)
    ax.set_aspect('equal') 
    ax.axis('off')
    ax.set_title(f"Turn {world.turn} - {len(world.nations)} Nations")
    
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='*', color='w', markerfacecolor='gold', markersize=10, label='Capital'),
        Patch(facecolor='grey', hatch='...', label='Mountain (Darker)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    
    st.pyplot(fig)

with col2:
    st.subheader("Nation Intelligence")
    
    def format_nation_option(nation_id):
        n = world.nations[nation_id]
        return n.name

    selected_nation_id = st.selectbox(
        "Select Nation to Analyze", 
        list(world.nations.keys()),
        format_func=format_nation_option
    )
    
    if selected_nation_id:
        nation = world.nations[selected_nation_id]
        
        c1, c2 = st.columns([1, 5])
        with c1:
            st.color_picker("Flag", nation.color, disabled=True, label_visibility="collapsed")
        with c2:
            st.markdown(f"### {nation.name}")
        
        st.markdown("#### 🕵️‍♂️ Spatial Intelligence Report")
        st.info("This text is generated deterministically from the map topology and injected into the Agent's prompt.")
        
        report = translator.generate_intelligence_report(selected_nation_id)
        st.markdown(report)
        
        st.divider()
        
        st.metric("Provinces", len(nation.province_ids))
        total_food = sum([world.provinces[pid].resources.food for pid in nation.province_ids])
        total_energy = sum([world.provinces[pid].resources.energy for pid in nation.province_ids])
        
        st.write("#### Resource Stockpiles")
        st.progress(min(1.0, total_food / 5000), text=f"Food: {int(total_food)}")
        st.progress(min(1.0, total_energy / 5000), text=f"Energy: {int(total_energy)}")

st.subheader("Diplomatic Trust Matrix")
import pandas as pd
df_trust = pd.DataFrame(world.trust_matrix)
st.dataframe(df_trust.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=1))

# --- HISTORY LOG ---
st.subheader("📜 Genesis History Log")
with st.expander("View Ancient History (50 Years)"):
    for event in world.global_events:
        st.text(event)
