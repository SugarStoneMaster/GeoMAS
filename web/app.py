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
from geomas.db import SimulationDB

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

# --- DIALOGS ---
@st.dialog("Seleziona Scenario")
def scenario_selection_dialog(num_turns: int):
    sim = st.session_state.get("sim")
    if not sim:
        st.error("Simulation not initialized.")
        return

    st.markdown(f"Scegli se attivare uno scenario durante questa run di **{num_turns} turni**.")
    
    # Calculate midpoint trigger
    midpoint = num_turns // 2
    trigger_turn = sim.world.turn + midpoint
    
    st.info(f"Lo scenario verrà innescato al turno **{trigger_turn}** (tra {midpoint} turni).")
    
    choice = st.selectbox("Scenario Type", ["Nessuno", "PANDEMIA", "SCOPERTA RISORSE", "INSURREZIONE"], index=0)
    
    if st.button("🚀 Conferma e Avvia", type="primary", use_container_width=True):
        import json
        st.session_state["remaining_turns"] = num_turns
        st.session_state["total_run_turns"] = num_turns
        st.session_state["scenario_trigger_turn"] = trigger_turn
        
        if choice in ["PANDEMIA", "SCOPERTA RISORSE", "INSURREZIONE"]:
            scenario_data = {"type": choice, "turn": trigger_turn}
            sim.planned_scenario = scenario_data
            if sim.db:
                sim.db.update_simulation_scenario(sim.simulation_id, json.dumps(scenario_data))
            st.session_state["enable_scenarios"] = True
            st.session_state["scenario_type"] = choice
        else:
            sim.planned_scenario = None
            if sim.db:
                sim.db.update_simulation_scenario(sim.simulation_id, None)
            st.session_state["enable_scenarios"] = False
            
        st.rerun()


# --- SESSION STATE INIT ---
if "sim" not in st.session_state:
    st.session_state["sim"] = None
if "remaining_turns" not in st.session_state:
    st.session_state["remaining_turns"] = 0
if "injections" not in st.session_state:
    st.session_state["injections"] = []



# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("🕹️ Controls")
    
    # Mode Selection
    mode = st.radio("Mode", ["Live Simulation", "Analysis / Forking"], index=0, key="app_mode")
    
    st.divider()
    
    if mode == "Analysis / Forking":
        # 0. Simulation Selection
        db_path = "data/simulation.duckdb"
        if os.path.exists(db_path):
            with SimulationDB(db_path) as db:
                sims = db.get_simulations()
            
            if not sims:
                st.warning("No simulations found in DB.")
            else:
                sim_options = {s['id']: f"Sim {s['id']} ({s['name']}) - T{s['total_turns']}" for s in sims}
                selected_sim_id = st.selectbox(
                    "Select Simulation", 
                    options=sorted(sim_options.keys(), reverse=True),
                    format_func=lambda x: sim_options[x]
                )
                
                # Load logic if selection changes or sim not loaded
                current_sim = st.session_state.get("sim")
                if not current_sim or current_sim.simulation_id != selected_sim_id:
                    if st.button(f"📥 Load Simulation {selected_sim_id}", type="primary"):
                        with st.spinner("Loading Simulation..."):
                            # Fetch metadata from DB to ensure consistent engine params
                            with SimulationDB(db_path) as db:
                                info = db.get_simulation_info(selected_sim_id)
                            
                            if info:
                                # Initialize Engine with original parameters
                                new_sim = SimulationEngine(
                                    map_seed=info['genesis_seed'],
                                    history_seed=info['simulation_seed'],
                                    n_cells=info['n_cells'],
                                    n_nations=info.get('n_nations', 4), # Fallback for old DBs
                                    db_path=db_path,
                                    simulation_id=selected_sim_id
                                )
                            else:
                                # Fallback
                                new_sim = SimulationEngine(
                                    db_path=db_path,
                                    simulation_id=selected_sim_id
                                )
                            # Load max turn state
                            max_turn = new_sim.db.get_max_turn(selected_sim_id)
                            if max_turn > 0:
                                new_sim.load_state(max_turn)
                            
                            st.session_state["sim"] = new_sim
                            st.session_state["remaining_turns"] = 0
                            
                            # Sync Scenario state
                            if new_sim.planned_scenario:
                                st.session_state["enable_scenarios"] = True
                                st.session_state["scenario_type"] = new_sim.planned_scenario.get("type", "PANDEMIA")
                                st.session_state["scenario_trigger_turn"] = new_sim.planned_scenario.get("turn", -1)
                            else:
                                st.session_state["enable_scenarios"] = False
                                
                            st.rerun()

        sim = st.session_state.get("sim")
        if sim and sim.db:
            st.markdown("### 🔍 Time Travel")
            max_turn = st.session_state["sim"].db.get_max_turn(sim.simulation_id)
            current_turn = st.session_state["sim"].world.turn
            
            target_turn = st.slider("Target Turn", 1, max_turn, current_turn)
            
            if st.button("📂 Load State", use_container_width=True):
                with st.spinner(f"Loading turn {target_turn}..."):
                    st.session_state["sim"].load_state(target_turn)
                    st.success(f"Loaded Turn {target_turn}")
                    st.rerun()
            
            st.markdown("### 🧪 Counterfactual Injection")
            
            # Injection State
            if "injections" not in st.session_state:
                st.session_state["injections"] = []

            # 1. Select Target
            target_nation = st.selectbox("Nation", sorted(list(st.session_state["sim"].world.nations.keys())))
            target_role = st.selectbox("Minister", ["Defense", "Economy", "Foreign"])
            
            # 2. Select Action based on Role
            from geomas.actions.defense.schemas import DefenseActionType
            from geomas.actions.economy.schemas import EconomicActionType
            from geomas.actions.foreign.schemas import ForeignActionType
            
            action_options = []
            if target_role == "Defense":
                action_options = [a.value for a in DefenseActionType]
            elif target_role == "Economy":
                action_options = [a.value for a in EconomicActionType]
            elif target_role == "Foreign":
                action_options = [a.value for a in ForeignActionType]
            
            target_action = st.selectbox("Action", action_options)
            action_details = st.text_input("Details (optional)", placeholder="e.g. qty=50, target=VULCANIA", help="Additional constraints for the action")
            
            constraint_type = st.radio("Constraint", ["FORBID", "FORCE"], horizontal=True)
            
            # 3. Add Injection
            if st.button("➕ Add Constraint"):
                injection = {
                    "nation_id": target_nation,
                    "role": target_role,
                    "action": target_action,
                    "details": action_details,
                    "type": constraint_type
                }
                st.session_state["injections"].append(injection)
                st.success(f"Added: {constraint_type} {target_action} for {target_nation} {target_role}")

            # 4. List Injections
            if st.session_state["injections"]:
                st.markdown("#### Active Constraints")
                for i, inj in enumerate(st.session_state["injections"]):
                    details_str = f" ({inj['details']})" if inj['details'] else ""
                    st.caption(f"{i+1}. {inj['nation_id']} ({inj['role']}): **{inj['type']} {inj['action']}**{details_str}")
                
                if st.button("Clear All"):
                    st.session_state["injections"] = []
                    st.rerun()
            
            st.divider()
            
            if st.button("🍴 Run Fork (5 Turns)", type="primary", use_container_width=True):
                 st.session_state["remaining_turns"] = 5
                 # Set a flag to indicate we are running a fork with injections
                 st.session_state["fork_active"] = True
                 st.rerun()
        else:
            st.warning("Initialize Simulation first.")
    
    else:
        # Live Simulation Info
        if st.session_state.get("sim"):
             st.markdown(f"### Current Turn: {st.session_state['sim'].world.turn}")


# --- TOP CONFIG (Visible in Live Mode or if Sim not init) ---
if not st.session_state["sim"] or mode == "Live Simulation":
    ctrl_cols = st.columns([1, 1, 1, 1, 1])

    with ctrl_cols[0]:
        map_seed = st.number_input("Map Seed", value=42, step=1, key="map_seed")

    with ctrl_cols[1]:
        history_seed = st.number_input("History Seed", value=99, step=1, key="history_seed")

    with ctrl_cols[2]:
        n_cells = st.number_input("Cells", value=300, min_value=50, max_value=3000, step=50, key="n_cells")
        n_nations = st.slider("Nations", min_value=4, max_value=10, value=4, key="n_nations")

    # Initialize session state (Already done at top)


    with ctrl_cols[3]:
        st.markdown("&nbsp;")  # Spacer for alignment
        if st.button("🔄 Init/Reset (Real LLM)", use_container_width=True):
            # Initialize Real LLM Client
            try:
                client = LLMClient()
            except Exception as e:
                st.error(f"LLM Error: {e}")
                st.stop()

            # Ensure data directory exists
            os.makedirs("data", exist_ok=True)
            db_path = "data/simulation.duckdb"
                
            # Create NEW Simulation (Auto-increment ID)
            sim = SimulationEngine(
                map_seed=int(map_seed),
                history_seed=int(history_seed),
                n_cells=int(n_cells),
                n_nations=int(n_nations),
                llm_client=client,
                db_path=db_path, # Always persist
                simulation_id=None # Force new ID creation
            )
            st.session_state["sim"] = sim
            st.session_state["remaining_turns"] = 0
            st.session_state["nation_index"] = 0
            st.rerun()

        if st.session_state["sim"]:
            if st.button("🔓 Release DB Connection", use_container_width=True, help="Close DuckDB file lock to allow external access"):
                if st.session_state["sim"].db:
                    st.session_state["sim"].close()
                    st.success("Database connection released.")

    sim = st.session_state["sim"]

    with ctrl_cols[4]:
        if sim:
            st.markdown(f"**Turn: {sim.world.turn}**")
            
            # --- CONTROL PANEL ---
            # If running, show Stop button
            if st.session_state["remaining_turns"] != 0:
                if st.button("⏹️ Stop Simulation", use_container_width=True, type="primary"):
                    st.session_state["remaining_turns"] = 0
                    sim.close()
                    st.rerun()
                
                status_desc = "Autoplay" if st.session_state["remaining_turns"] == -1 else f"{st.session_state['remaining_turns']} turns remaining"
                st.caption(f"Status: **Running ({status_desc})**")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("⏭️ Step 1", use_container_width=True):
                        st.session_state["remaining_turns"] = 1
                        st.session_state["total_run_turns"] = 1
                        st.session_state["scenario_trigger_turn"] = sim.world.turn
                        st.rerun()
                    if st.button("⏩ Run 5", use_container_width=True):
                        scenario_selection_dialog(5)
                with c2:
                    if st.button("🚀 Run 100", use_container_width=True):
                        scenario_selection_dialog(100)
                    if st.button("🌀 Run 25 Turns", type="primary", use_container_width=True):
                        scenario_selection_dialog(25)
                
                cols_n = st.columns([1, 2])
                with cols_n[0]:
                    n_val = st.number_input("Turns", min_value=1, value=10, label_visibility="collapsed", key="run_n_val")
                with cols_n[1]:
                    if st.button(f"▶️ Run {n_val}", use_container_width=True):
                        scenario_selection_dialog(n_val)
                
                # DB Status bit
                if sim.db and sim.db._conn is not None:
                    st.caption("🟢 Database Connected")
                else:
                    st.caption("⚪ Database Released")
                
                # Planned Scenario Info
                if sim.planned_scenario:
                    st.info(f"🌪️ Planned: {sim.planned_scenario['type']} (T{sim.planned_scenario['turn']})")
        else:
            st.markdown("&nbsp;")
            st.info("Click Init/Reset")

else:
    # Analysis Mode: Ensure 'sim' is available (for compatibility with lower blocks)
    sim = st.session_state["sim"]
    if sim:
        st.success(f"Analysis Mode Active: Viewing Turn {sim.world.turn}")

# --- AUTO-RUN LOOP ---
if st.session_state["remaining_turns"] != 0 and sim:
    # Get active injections if any
    active_injections = st.session_state.get("injections", [])
    
    # Determine Scenario Trigger
    scenario_trigger = None
    
    # Check for manual trigger first
    if "manual_scenario_trigger" in st.session_state:
        scenario_trigger = st.session_state.pop("manual_scenario_trigger")
        st.toast(f"🚨 Executing Manual Scenario: {scenario_trigger['type']}!", icon="🔥")
    # Otherwise check for midpoint trigger
    elif st.session_state.get("enable_scenarios", False) and st.session_state["remaining_turns"] > 0:
        # If we know exactly how many turns total we're running
        if "total_run_turns" in st.session_state:
            target_turn = st.session_state.get("scenario_trigger_turn", -1)
            if target_turn == sim.world.turn:
                scenario_trigger = {
                    "type": st.session_state.get("scenario_type", "PANDEMIA"),
                    "turn": target_turn
                }
                st.toast(f"🚨 Executing Scenario: {scenario_trigger['type']}!", icon="🔥")

    
    # Perform one step
    sim.step(injections=active_injections, scenario_trigger=scenario_trigger)
    
    # CLEAR INJECTIONS after one use (make them one-shot)
    if active_injections:
        st.session_state["injections"] = []
        st.toast("🧪 One-shot injection applied and cleared.", icon="⚡")
    
    # Decrement if not Autoplay
    if st.session_state["remaining_turns"] > 0:
        st.session_state["remaining_turns"] -= 1
    
    # If we just reached zero (end of a run), release connection automatically
    if st.session_state["remaining_turns"] == 0:
        sim.close()
        
    st.rerun()

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
