"""
GeoMAS Dashboard - Main Application.

Streamlit-based UI for the geopolitical simulation.
Run with: streamlit run web/app.py
"""

import streamlit as st
import sys
import os
import json
import time
import multiprocessing

# --- MULTIPROCESSING GUARD FOR MACOS ---
# Streamlit re-runs the script in workers on macOS 'spawn'.
# We MUST NOT use sys.exit(0) here as workers need to stay alive to handle tasks.
# Instead, we wrap the UI logic to only run in the MainProcess.
IS_MAIN = multiprocessing.current_process().name == "MainProcess"

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
from web.components.event_log import render_event_log
from geomas.simulation.parallel_runner import ParallelBatchManager


# --- MAIN UI EXECUTION ---
if IS_MAIN:
    # --- PAGE CONFIG ---
    st.set_page_config(page_title="GeoMAS Dashboard", layout="wide")
    st.title("👑 GeoMAS: Simulation Dashboard")

    # Check GENESIS_ENABLED env flag once at load time
    GENESIS_ENABLED = os.environ.get("GENESIS_ENABLED", "false").lower() == "true"

    # --- SESSION STATE INIT ---
    if "sim" not in st.session_state:
        st.session_state["sim"] = None
    if "remaining_turns" not in st.session_state:
        st.session_state["remaining_turns"] = 0
    if "injections" not in st.session_state:
        st.session_state["injections"] = []
    if "parallel_mode" not in st.session_state:
        st.session_state["parallel_mode"] = False
    if "parallel_instances" not in st.session_state:
        st.session_state["parallel_instances"] = 3
    if "parallel_dry_run" not in st.session_state:
        st.session_state["parallel_dry_run"] = True
    if "parallel_running" not in st.session_state:
        st.session_state["parallel_running"] = False

    # --- DIALOGS ---
    @st.dialog("Seleziona Scenario")
    def scenario_selection_dialog(num_turns: int):
        sim = st.session_state.get("sim")
        if not sim:
            st.error("Simulation not initialized.")
            return

        st.markdown(f"Scegli se attivare uno scenario durante questa run di **{num_turns} turni**.")
        midpoint = num_turns // 2
        default_trigger = sim.world.turn + midpoint
        max_trigger = sim.world.turn + num_turns

        trigger_turn = st.slider(
            "Trigger scenario at turn",
            min_value=sim.world.turn + 1,
            max_value=max_trigger,
            value=default_trigger,
            help="Choose at which turn the scenario fires. Default is the midpoint of the run."
        )
        st.caption(f"Scenario fires in **{trigger_turn - sim.world.turn}** turns (turn **{trigger_turn}**).")

        choice = st.selectbox("Scenario Type", ["Nessuno", "PANDEMIA", "SCOPERTA RISORSE", "INSURREZIONE", "CAMBIO GOVERNO"], index=0)

        target_nation = None
        new_gov = None
        new_strat = None
        # Extra params for configurable scenarios
        rd_target_nation = None
        rd_target_province = None
        ins_target_nation = None
        ins_start_province = None
        ins_steal_pct = 0.25

        nation_ids = sorted(list(sim.world.nations.keys()))

        if choice == "CAMBIO GOVERNO":
            from geomas.agents.schemas.protocol import GovernmentType
            from geomas.agents.schemas import GlobalStrategy
            
            col1, col2, col3 = st.columns(3)
            with col1:
                 target_nation = st.selectbox("Nazione Target", nation_ids, key="dlg_rc_nation")
            with col2:
                 new_gov = st.selectbox("Nuovo Governo", [g.value for g in GovernmentType], key="dlg_rc_gov")
            with col3:
                 new_strat = st.selectbox("Nuova Strategia", [s.value for s in GlobalStrategy], key="dlg_rc_strat")

        elif choice == "SCOPERTA RISORSE":
            st.markdown("**Configurazione Scoperta Risorse** *(lascia vuoto per selezione automatica)*")
            col1, col2 = st.columns(2)
            with col1:
                rd_target_nation = st.selectbox(
                    "Nazione (opzionale)", ["-- Automatico --"] + nation_ids, key="dlg_rd_nation"
                )
                rd_target_nation = None if rd_target_nation == "-- Automatico --" else rd_target_nation

            with col2:
                # Province selection only available when a nation is chosen
                if rd_target_nation:
                    nation_provinces = sorted(
                        [pid for pid, p in sim.world.provinces.items() if p.owner_id == rd_target_nation]
                    )
                    rd_province_opts = ["-- Automatico --"] + [str(pid) for pid in nation_provinces]
                    rd_prov_sel = st.selectbox("Provincia (opzionale)", rd_province_opts, key="dlg_rd_prov")
                    rd_target_province = None if rd_prov_sel == "-- Automatico --" else int(rd_prov_sel)
                else:
                    st.caption("Seleziona prima una nazione per scegliere la provincia.")

        elif choice == "INSURREZIONE":
            st.markdown("**Configurazione Insurrezione** *(lascia vuoto per selezione automatica)*")
            col1, col2 = st.columns(2)
            with col1:
                ins_target_nation = st.selectbox(
                    "Nazione Madrepatria (opzionale)", ["-- Automatico --"] + nation_ids, key="dlg_ins_nation"
                )
                ins_target_nation = None if ins_target_nation == "-- Automatico --" else ins_target_nation

            with col2:
                if ins_target_nation:
                    nation_provinces = sorted(
                        [pid for pid, p in sim.world.provinces.items() if p.owner_id == ins_target_nation]
                    )
                    ins_province_opts = ["-- Automatico --"] + [str(pid) for pid in nation_provinces]
                    ins_prov_sel = st.selectbox("Provincia di Partenza BFS (opzionale)", ins_province_opts, key="dlg_ins_prov")
                    ins_start_province = None if ins_prov_sel == "-- Automatico --" else int(ins_prov_sel)
                else:
                    st.caption("Seleziona prima una nazione per scegliere la provincia.")

            ins_steal_pct = st.slider(
                "% Territorio Ribelle", min_value=5, max_value=75, value=25, step=5,
                help="Percentuale del territorio della madrepatria che si separa.",
                key="dlg_ins_pct"
            ) / 100.0

        st.divider()

        if st.button("🚀 Conferma e Avvia", type="primary", use_container_width=True):
            if choice in ["PANDEMIA", "SCOPERTA RISORSE", "INSURREZIONE", "CAMBIO GOVERNO"]:
                scenario_data = {"type": choice, "turn": trigger_turn}
                if choice == "CAMBIO GOVERNO":
                    scenario_data["target_id"] = target_nation
                    scenario_data["new_gov"] = new_gov
                    scenario_data["new_strategy"] = new_strat
                elif choice == "SCOPERTA RISORSE":
                    if rd_target_nation:
                        scenario_data["target_nation_id"] = rd_target_nation
                    if rd_target_province is not None:
                        scenario_data["target_province_id"] = rd_target_province
                elif choice == "INSURREZIONE":
                    if ins_target_nation:
                        scenario_data["target_nation_id"] = ins_target_nation
                    if ins_start_province is not None:
                        scenario_data["start_province_id"] = ins_start_province
                    scenario_data["steal_percentage"] = ins_steal_pct

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


            if st.session_state.get("parallel_mode"):
                manager = ParallelBatchManager(n_workers=st.session_state["parallel_instances"])
                progress_bar = st.progress(0, text="Initializing parallel batch...")
                
                def update_progress(current, total, msg=None):
                    progress = current / total
                    text = msg or f"Simulating: {current}/{total} instances finished"
                    progress_bar.progress(progress, text=text)
                
                map_seed = st.session_state.get("map_seed", 42)
                hist_seed = st.session_state.get("history_seed", 99)
                n_cells = st.session_state.get("n_cells", 300)
                n_nations = st.session_state.get("n_nations", 4)
                
                manager.run_batch(
                    n_turns=num_turns,
                    map_seed=int(map_seed),
                    history_seed=int(hist_seed),
                    n_cells=int(n_cells),
                    n_nations=int(n_nations),
                    planned_scenario=sim.planned_scenario,
                    progress_callback=update_progress,
                    use_mock=st.session_state.get("parallel_dry_run", False)
                )
                
                st.success(f"Successfully finished {st.session_state['parallel_instances']} parallel runs!")
                time.sleep(2)
                st.session_state["remaining_turns"] = 0
            else:
                st.session_state["remaining_turns"] = num_turns
                st.session_state["total_run_turns"] = num_turns
                st.session_state["scenario_trigger_turn"] = trigger_turn

            st.rerun()


    # --- SIDEBAR CONTROLS ---
    with st.sidebar:
        st.title("🕹️ Controls")
        
        # Mode Selection
        mode = st.radio("Mode", ["Live Simulation", "Analysis / Forking"], index=0, key="app_mode")
        
        st.divider()
        
        if mode == "Live Simulation":
            st.markdown("### 🧬 Parallel Execution")
            st.session_state["parallel_mode"] = st.checkbox("Enable Parallel Mode", value=st.session_state["parallel_mode"], help="Run multiple simulations concurrently with same seed.")
            if st.session_state["parallel_mode"]:
                st.session_state["parallel_instances"] = st.slider("Instances", 2, 6, st.session_state["parallel_instances"])
                st.session_state["parallel_dry_run"] = st.checkbox("Parallel Dry Run", value=st.session_state["parallel_dry_run"], help="Use Mock LLM (zero cost, high speed) for all parallel instances.")
                st.info("💡 Useful for variance analysis. Each run uses unique DB workers, merged at end.")
            st.divider()
        
        if mode == "Analysis / Forking":
            # 0. Simulation Selection
            db_path = "data/simulation.duckdb"
            if os.path.exists(db_path):
                # Use read_only=True for listing; avoids locking if other processes are writing
                with SimulationDB(db_path, read_only=True) as db:
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
                            with st.spinner(f"Loading Sim {selected_sim_id}..."):
                                # Use read_only=True to browse history
                                with SimulationDB(db_path, read_only=True) as db:
                                    info = db.get_simulation_info(selected_sim_id)
                                
                                if info:
                                    # Initialize Engine with original parameters
                                    new_sim = SimulationEngine(
                                        map_seed=info['genesis_seed'],
                                        history_seed=info['simulation_seed'],
                                        n_cells=info['n_cells'],
                                        n_nations=info.get('n_nations', 4), # Fallback for old DBs
                                        db_path=db_path,
                                        simulation_id=selected_sim_id,
                                        read_only=True
                                    )
                                else:
                                    # Fallback
                                    new_sim = SimulationEngine(
                                        db_path=db_path,
                                        simulation_id=selected_sim_id,
                                        read_only=True
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
                
                st.markdown("### 🌍 Scenario Events")
                scenario_opts = ["Non-scenario", "PANDEMIA", "RESOURCE_DISCOVERY", "INSURRECTION", "REGIME_CHANGE"]
                selected_scenario = st.selectbox("Trigger Scenario", scenario_opts, index=0)
                
                # Constrain trigger strictly within the remaining turns of the loaded simulation
                if current_turn >= max_turn:
                    # Simulation is completely finished, cannot trigger scenarios in the past/present
                    target_scenario_turn = current_turn
                    st.info(f"Simulation is at maximum turn ({max_turn}). No future turns available for scenario injection.")
                else:
                    slider_max = max(current_turn + 1, max_turn)
                    target_scenario_turn = st.slider("Trigger Turn", current_turn, slider_max, current_turn)
                
                if selected_scenario == "REGIME_CHANGE":
                    from geomas.agents.schemas.protocol import GovernmentType
                    from geomas.agents.schemas import GlobalStrategy
                    
                    c_nat, c_gov, c_strat = st.columns(3)
                    with c_nat:
                        st.session_state["scenario_rc_target"] = st.selectbox("Target Nation", sorted(list(sim.world.nations.keys())), key="sb_rc_nation")
                    with c_gov:
                        st.session_state["scenario_rc_gov"] = st.selectbox("New Government", [g.value for g in GovernmentType], key="sb_rc_gov")
                    with c_strat:
                        st.session_state["scenario_rc_strat"] = st.selectbox("New Strategy", [s.value for s in GlobalStrategy], key="sb_rc_strat")

                elif selected_scenario == "RESOURCE_DISCOVERY":
                    st.markdown("**Resource Discovery Config** *(leave blank for auto)*")
                    all_nation_ids = sorted(list(sim.world.nations.keys()))
                    col1, col2 = st.columns(2)
                    with col1:
                        rd_nation = st.selectbox("Nation (optional)", ["-- Auto --"] + all_nation_ids, key="sb_rd_nation")
                        st.session_state["scenario_rd_nation"] = None if rd_nation == "-- Auto --" else rd_nation
                    with col2:
                        if st.session_state.get("scenario_rd_nation"):
                            prov_ids = sorted([pid for pid, p in sim.world.provinces.items() if p.owner_id == st.session_state["scenario_rd_nation"]])
                            prov_sel = st.selectbox("Province (optional)", ["-- Auto --"] + [str(pid) for pid in prov_ids], key="sb_rd_prov")
                            st.session_state["scenario_rd_province"] = None if prov_sel == "-- Auto --" else int(prov_sel)
                        else:
                            st.caption("Select a nation first.")

                elif selected_scenario == "INSURRECTION":
                    st.markdown("**Insurrection Config** *(leave blank for auto)*")
                    all_nation_ids = sorted(list(sim.world.nations.keys()))
                    col1, col2 = st.columns(2)
                    with col1:
                        ins_nation = st.selectbox("Motherland (optional)", ["-- Auto --"] + all_nation_ids, key="sb_ins_nation")
                        st.session_state["scenario_ins_nation"] = None if ins_nation == "-- Auto --" else ins_nation
                    with col2:
                        if st.session_state.get("scenario_ins_nation"):
                            prov_ids = sorted([pid for pid, p in sim.world.provinces.items() if p.owner_id == st.session_state["scenario_ins_nation"]])
                            prov_sel = st.selectbox("Starting Province BFS (optional)", ["-- Auto --"] + [str(pid) for pid in prov_ids], key="sb_ins_prov")
                            st.session_state["scenario_ins_province"] = None if prov_sel == "-- Auto --" else int(prov_sel)
                        else:
                            st.caption("Select a nation first.")
                    st.session_state["scenario_ins_pct"] = st.slider(
                        "% Rebel Territory", min_value=5, max_value=75, value=25, step=5,
                        help="Fraction of the motherland that rebels.", key="sb_ins_pct"
                    ) / 100.0
                

                # Show current staged scenario (if any)
                staged = st.session_state.get("manual_scenario_trigger")
                if staged:
                    st.success(f"✅ Staged: **{staged['type']}** @ Turn {staged['turn']}")
                    if st.button("❌ Clear Scenario", use_container_width=True):
                        st.session_state.pop("manual_scenario_trigger", None)
                        st.session_state["enable_scenarios"] = False
                        st.rerun()
                        
                # Gate scenario assignment behind an explicit confirm button.
                # FIX: Without this gate, the trigger would be re-created on every Streamlit
                # rerun as `current_turn` advances, causing the scenario to fire again
                # in subsequent turns (observed when running a fork with 2 remaining turns).
                if selected_scenario != "Non-scenario":
                    if st.button("📌 Stage Scenario", use_container_width=True):
                        trigger_data = {"type": selected_scenario, "turn": target_scenario_turn}
                        if selected_scenario == "REGIME_CHANGE":
                            trigger_data["target_id"] = st.session_state.get("scenario_rc_target")
                            trigger_data["new_gov"] = st.session_state.get("scenario_rc_gov")
                            trigger_data["new_strategy"] = st.session_state.get("scenario_rc_strat")
                        elif selected_scenario == "RESOURCE_DISCOVERY":
                            rd_n = st.session_state.get("scenario_rd_nation")
                            rd_p = st.session_state.get("scenario_rd_province")
                            if rd_n:
                                trigger_data["target_nation_id"] = rd_n
                            if rd_p is not None:
                                trigger_data["target_province_id"] = rd_p
                        elif selected_scenario == "INSURRECTION":
                            ins_n = st.session_state.get("scenario_ins_nation")
                            ins_p = st.session_state.get("scenario_ins_province")
                            ins_pct = st.session_state.get("scenario_ins_pct", 0.25)
                            if ins_n:
                                trigger_data["target_nation_id"] = ins_n
                            if ins_p is not None:
                                trigger_data["start_province_id"] = ins_p
                            trigger_data["steal_percentage"] = ins_pct
                        st.session_state["manual_scenario_trigger"] = trigger_data
                        st.session_state["enable_scenarios"] = True
                        st.session_state["scenario_type"] = selected_scenario
                        st.session_state["scenario_trigger_turn"] = target_scenario_turn
                        st.rerun()
                else:
                    if not staged:
                        st.session_state["enable_scenarios"] = False
                        st.session_state["scenario_trigger_turn"] = -1
                
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
                
                # Duration config
                col_dur1, col_dur2 = st.columns([1, 1])
                with col_dur1:
                    is_infinite = st.checkbox("Infinite Duration (Until cleared)", value=False)
                with col_dur2:
                    dur_val = st.number_input("Duration (Months)", min_value=1, value=1, step=1, disabled=is_infinite)
                
                # 3. Add Injection
                if st.button("➕ Add Constraint"):
                    injection = {
                        "nation_id": target_nation,
                        "role": target_role,
                        "action": target_action,
                        "details": action_details,
                        "type": constraint_type,
                        "duration": 9999 if is_infinite else dur_val
                    }
                    st.session_state["injections"].append(injection)
                    st.success(f"Added: {constraint_type} {target_action} for {target_nation} {target_role}")

                # 4. List Injections
                if st.session_state["injections"]:
                    st.markdown("#### Active Constraints")
                    for i, inj in enumerate(st.session_state["injections"]):
                        details_str = f" ({inj['details']})" if inj['details'] else ""
                        dur_str = "∞" if inj.get("duration", 1) > 9000 else inj.get("duration", 1)
                        st.caption(f"{i+1}. {inj['nation_id']} ({inj['role']}): **{inj['type']} {inj['action']}**{details_str} [Dur: {dur_str}]")
                    
                    if st.button("Clear All"):
                        st.session_state["injections"] = []
                        st.rerun()
                
                st.divider()

                # Compute remaining turns = max_turn(source) - current_turn
                source_max_turn = sim.db.get_max_turn(sim.simulation_id)
                fork_remaining = max(1, source_max_turn - sim.world.turn)

                fork_btn_label = f"🍴 Run Fork ({fork_remaining} turns remaining)"
                fork_n_turns = st.number_input(
                    "Override turns (0 = auto)",
                    min_value=0,
                    value=0,
                    step=1,
                    help=(
                        f"Auto: runs {fork_remaining} turns (from current snapshot T{sim.world.turn} "
                        f"to source max T{source_max_turn}). Set > 0 to override."
                    )
                )
                effective_turns = int(fork_n_turns) if fork_n_turns > 0 else fork_remaining

                if st.button(fork_btn_label, type="primary", use_container_width=True):
                    st.session_state["remaining_turns"] = effective_turns
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
            if GENESIS_ENABLED:
                history_seed = st.number_input("History Seed", value=99, step=1, key="history_seed")
            else:
                history_seed = 99  # Fixed default when genesis is disabled
                st.caption("History Seed: N/A (Genesis disabled)")

        with ctrl_cols[2]:
            n_cells = st.number_input("Cells", value=300, min_value=50, max_value=3000, step=50, key="n_cells")
            n_nations = st.slider("Nations", min_value=4, max_value=10, value=4, key="n_nations")

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
        # 0. Check for Forking Detachment
        if st.session_state.get("fork_active", False):
            new_id = sim.fork()
            st.session_state["fork_active"] = False
            st.toast(f"🍴 Forked into new Simulation {new_id}!", icon="📂")
            
        # Get active injections if any
        active_injections = st.session_state.get("injections", [])
        
        # Determine Scenario Trigger
        scenario_trigger = None
        
        # Check for manual trigger first
        if "manual_scenario_trigger" in st.session_state:
            trigger = st.session_state["manual_scenario_trigger"]
            if trigger.get("turn") == sim.world.turn:
                scenario_trigger = st.session_state.pop("manual_scenario_trigger")
                st.toast(f"🚨 Executing Manual Scenario: {scenario_trigger['type']}!", icon="🔥")
        # Otherwise check for midpoint trigger or explicit fork trigger
        elif st.session_state.get("enable_scenarios", False) and st.session_state["remaining_turns"] > 0:
            target_turn = st.session_state.get("scenario_trigger_turn", -1)
            if target_turn == sim.world.turn:
                if getattr(sim, "planned_scenario", None) and sim.planned_scenario.get("turn") == target_turn:
                    scenario_trigger = sim.planned_scenario
                else:
                    scenario_trigger = {
                        "type": st.session_state.get("scenario_type", "PANDEMIA"),
                        "turn": target_turn
                    }
                st.toast(f"🚨 Executing Scenario: {scenario_trigger['type']}!", icon="🔥")

        
        # Perform one step
        sim.step(injections=active_injections, scenario_trigger=scenario_trigger)
        
        # Update active injections
        if active_injections:
            new_injections = []
            for inj in active_injections:
                if inj.get("duration", 1) > 1:
                    inj["duration"] -= 1
                    new_injections.append(inj)
            st.session_state["injections"] = new_injections
            
            if not new_injections:
                st.toast("🧪 All constraints expired and cleared.", icon="⚡")
        
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
    if c3.button("🌐 Global Events", use_container_width=True):
        st.session_state["active_tab"] = "EVENTS"
        st.rerun()

    st.divider()


    # --- MAIN VIEW ---
    if not sim:
        st.info("Initialize the simulation using the controls above.")
    else:
        world = sim.world

        # --- RENDER ACTIVE PAGE ---
        active_tab = st.session_state["active_tab"]

        if active_tab == "MAP":
            render_map_page(world)
        elif active_tab == "LOGS":
            render_logs_page(world, sim.history, sim.context_manager.global_events)
        elif active_tab == "EVENTS":
            st.subheader("🌐 Global Events")
            render_event_log(sim.context_manager.global_events)
