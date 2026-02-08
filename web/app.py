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
# Import local modules
from geomas.agents.llm_client import LLMClient
from web.views.map_page import render_map_page
from web.views.logs_page import render_logs_page
from web.views.deception_page import render_deception_page
from web.components.event_log import render_event_log


# --- PAGE CONFIG ---
st.set_page_config(page_title="GeoMAS Dashboard", layout="wide")
st.title("👑 GeoMAS: Simulation Dashboard")


# --- TOP CONTROLS (instead of sidebar) ---
ctrl_cols = st.columns([1, 1, 1, 1, 1])

with ctrl_cols[0]:
    map_seed = st.number_input("Map Seed", value=42, step=1, key="map_seed")

with ctrl_cols[1]:
    history_seed = st.number_input("History Seed", value=99, step=1, key="history_seed")

with ctrl_cols[2]:
    n_cells = st.number_input("Cells", value=1500, min_value=500, max_value=3000, step=100, key="n_cells")
    n_nations = st.slider("Nations", min_value=4, max_value=10, value=4, key="n_nations")

# Initialize session state
if "sim" not in st.session_state:
    st.session_state["sim"] = None

with ctrl_cols[3]:
    st.markdown("&nbsp;")  # Spacer for alignment
    if st.button("🔄 Init/Reset (Real LLM)", use_container_width=True):
        
        # Initialize Real LLM Client
        try:
            client = LLMClient()
        except Exception as e:
            st.error(f"LLM Error: {e}")
            st.stop()
            
        sim = SimulationEngine(
            map_seed=int(map_seed),
            history_seed=int(history_seed),
            n_cells=int(n_cells),
            n_nations=int(n_nations),
            llm_client=client
        )
        st.session_state["sim"] = sim
        st.session_state["nation_index"] = 0
        st.rerun()

sim = st.session_state["sim"]

with ctrl_cols[4]:
    if sim:
        st.markdown(f"**Turn: {sim.world.turn}**")
        if st.button("▶️ Next Turn", use_container_width=True):
            with st.spinner("Thinking..."):
                sim.step()
            st.rerun()
            
        if st.button("⏩ Run 5 Turns", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i in range(5):
                status_text.text(f"Running Turn {sim.world.turn}...")
                sim.step()
                progress_bar.progress((i + 1) / 5)
                
            status_text.empty()
            progress_bar.empty()
            st.rerun()
    else:
        st.markdown("&nbsp;")
        st.info("Click Init/Reset")

st.divider()


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


# --- MAIN VIEW ---
if not sim:
    st.info("Initialize the simulation using the controls above.")
    st.stop()

world = sim.world


# --- RENDER ACTIVE PAGE ---
active_tab = st.session_state["active_tab"]

if active_tab == "MAP":
    render_map_page(world)
elif active_tab == "LOGS":
    # 2-column layout for logs: History | Events
    tab_hist, tab_events = st.tabs(["Turn History", "Global Events"])
    with tab_hist:
        render_logs_page(world, sim.history, sim.context_manager.global_events)
    with tab_events:
        render_event_log(sim.context_manager.global_events)
elif active_tab == "DECEPTION":
    render_deception_page(world, sim.history)
