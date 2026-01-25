"""
GeoMAS Dashboard - Main Application.

Streamlit-based UI for the geopolitical simulation.
Run with: streamlit run web/app.py
"""

import streamlit as st
import sys
import os

# --- PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import simulation
from geomas.simulation import SimulationEngine

# Import local modules
from web.mock_client import UIMockLLM
from web.views.map_page import render_map_page
from web.views.logs_page import render_logs_page
from web.views.deception_page import render_deception_page


# --- PAGE CONFIG ---
st.set_page_config(page_title="GeoMAS Dashboard", layout="wide")
st.title("👑 GeoMAS: Simulation Dashboard")


# --- SIDEBAR: SIMULATION CONTROLS ---
st.sidebar.header("World Generation Parameters")

map_seed = st.sidebar.number_input("Map Seed (Geometry)", value=42, step=1)
history_seed = st.sidebar.number_input("History Seed (Genesis)", value=99, step=1)
n_cells = st.sidebar.slider("Map Resolution (Cells)", 500, 3000, 1500)
n_nations = 10
st.sidebar.info(f"Simulation fixed to {n_nations} Preset Nations")

# Initialize session state
if "sim" not in st.session_state:
    st.session_state["sim"] = None

# Initialize/Reset button
if st.sidebar.button("Initialize / Reset Simulation"):
    sim = SimulationEngine(
        map_seed=map_seed,
        history_seed=history_seed,
        n_cells=n_cells,
        llm_client=UIMockLLM()
    )
    st.session_state["sim"] = sim
    st.session_state["nation_index"] = 0
    st.success(f"Simulation Initialized with Map Seed {map_seed}!")
    st.rerun()

sim = st.session_state["sim"]

# Turn control
if sim:
    st.sidebar.markdown(f"### Turn: {sim.world.turn}")
    if st.sidebar.button("▶️ Run Next Turn"):
        with st.spinner("Agents are thinking..."):
            sim.step()
            st.success(f"Turn {sim.world.turn} Complete!")
            st.rerun()


# --- MAIN VIEW ---
if not sim:
    st.info("Please initialize the simulation from the sidebar.")
    st.stop()

world = sim.world


# --- TAB NAVIGATION ---
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "MAP"

c1, c2, c3 = st.columns([1, 1, 1])
if c1.button("🗺️ Map & Intel", use_container_width=True):
    st.session_state["active_tab"] = "MAP"
    st.rerun()
if c2.button("📜 History & Logs", use_container_width=True):
    st.session_state["active_tab"] = "LOGS"
    st.rerun()
if c3.button("🕵️ Deception Analysis", use_container_width=True):
    st.session_state["active_tab"] = "DECEPTION"
    st.rerun()

st.divider()


# --- RENDER ACTIVE PAGE ---
active_tab = st.session_state["active_tab"]

if active_tab == "MAP":
    render_map_page(world)
elif active_tab == "LOGS":
    render_logs_page(world, sim.history)
elif active_tab == "DECEPTION":
    render_deception_page(world, sim.history)
