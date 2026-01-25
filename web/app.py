import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Patch
from matplotlib.collections import PatchCollection
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd # Added pandas
import sys
import os
from typing import Type

# --- PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import Core Modules
from geomas.simulation import SimulationEngine
from geomas.schemas.world import TerrainType 
from geomas.world.spatial import SpatialTranslator
from geomas.agents.llm_client import LLMClient
from geomas.schemas.protocol import (
    CountryEnvelope, GlobalStrategy, PublicIntent, 
    MilitaryPayload, MilitaryIntent, MilitaryIntentType,
    EconomicPayload, EconomicIntent, EconomicIntentType,
    ForeignPayload, ForeignIntent, ForeignIntentType,
    DefenseProposal, EconomicProposal, ForeignProposal
)
from geomas.schemas.actions import ActionType, DecisionSource
from geomas.analysis.deception import DeceptionAnalyzer

# --- MOCK CLIENT FOR UI ---
class UIMockLLM(LLMClient):
    def __init__(self): pass
    
    def query_agent(self, system_prompt, user_prompt, response_model, max_retries=3):
        # Return valid dummy objects
        if response_model == DefenseProposal:
            return DefenseProposal(
                intent=MilitaryIntent(type=MilitaryIntentType.IDLE, reasoning="Peace is good"),
                payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                urgency=1
            )
        elif response_model == EconomicProposal:
            return EconomicProposal(
                intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="We need to grow"),
                payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE, action_type=ActionType.INVEST_WELFARE),
                projected_cost=50.0
            )
        elif response_model == ForeignProposal:
            return ForeignProposal(
                intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Friends are good"),
                payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE, action_type=ActionType.SEND_DIPLOMATIC_MESSAGE),
                target_trust_impact=0.1
            )
        elif response_model == CountryEnvelope:
            return CountryEnvelope(
                turn=1, # Will be overwritten
                sender_id="TEST", # Will be overwritten
                global_strategy=GlobalStrategy.COALITION_BUILDER,
                public_statement="We are investing in our people and seeking peace.",
                public_intent=PublicIntent.PEACEFUL,
                military_payload=MilitaryPayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
                military_intent=MilitaryIntent(type=MilitaryIntentType.IDLE, reasoning="No threats detected."),
                economic_payload=EconomicPayload(
                    source=DecisionSource.MINISTRY_ADVICE, 
                    action_type=ActionType.INVEST_WELFARE,
                    parameters={"amount": 50.0}
                ),
                economic_intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="Boosting satisfaction."),
                foreign_payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
                foreign_intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="Maintaining status quo.")
            )
        return response_model()

st.set_page_config(page_title="GeoMAS Dashboard", layout="wide")

st.title("👑 GeoMAS: Simulation Dashboard")

# --- SIDEBAR CONFIG ---
st.sidebar.header("World Generation Parameters")

map_seed = st.sidebar.number_input("Map Seed (Geometry)", value=42, step=1)
history_seed = st.sidebar.number_input("History Seed (Genesis)", value=99, step=1)
n_cells = st.sidebar.slider("Map Resolution (Cells)", 500, 3000, 1500)
n_nations = 10 
st.sidebar.info(f"Simulation fixed to {n_nations} Preset Nations")

if "sim" not in st.session_state:
    st.session_state["sim"] = None

if st.sidebar.button("Initialize / Reset Simulation"):
    sim = SimulationEngine(map_seed=map_seed, history_seed=history_seed, n_cells=n_cells, llm_client=UIMockLLM())
    st.session_state["sim"] = sim
    st.session_state["turn_history"] = [] 
    st.session_state["nation_index"] = 0
    st.success(f"Simulation Initialized with Map Seed {map_seed}!")
    st.rerun() 

sim = st.session_state["sim"]

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
translator = SpatialTranslator(world)

# --- CUSTOM TAB NAVIGATION ---
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "MAP"

# Navigation Buttons
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

# Render Content based on active_tab
if st.session_state["active_tab"] == "MAP":
    col1, col2 = st.columns([3, 2])

    def darken_color(hex_color, factor=0.7):
        rgb = mcolors.hex2color(hex_color)
        darker_rgb = [max(0, c * factor) for c in rgb]
        return mcolors.to_hex(darker_rgb)

    with col1:
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
        st.pyplot(fig)

    with col2:
        def format_nation_option(nation_id):
            n = world.nations[nation_id]
            return n.name
        
        nation_ids = list(world.nations.keys())
        
        if "nation_index" not in st.session_state:
            st.session_state["nation_index"] = 0
            
        selected_nation_id = st.selectbox(
            "Select Nation", 
            nation_ids,
            format_func=format_nation_option,
            index=st.session_state["nation_index"],
            key="nation_selector"
        )
        
        if selected_nation_id:
            st.session_state["nation_index"] = nation_ids.index(selected_nation_id)
            
            nation = world.nations[selected_nation_id]
            st.markdown(f"### {nation.name}")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Budget", f"{nation.total_budget:.0f}")
            c2.metric("Satisfaction", f"{nation.internal_state.public_satisfaction:.2f}")
            c3.metric("Population", f"{nation.total_population:,}")
            c4.metric("Power", f"{nation.power_projection:.1f}")
            
            st.progress(min(1.0, nation.total_food / 10000), text=f"Food: {nation.total_food:.0f}")
            st.progress(min(1.0, nation.total_energy / 5000), text=f"Energy: {nation.total_energy:.0f}")
            st.progress(min(1.0, nation.total_materials / 5000), text=f"Materials: {nation.total_materials:.0f}")
            
            st.markdown("#### 🕵️‍♂️ Spatial Intelligence Report")
            report = translator.generate_intelligence_report(selected_nation_id)
            st.markdown(report)
            
    # --- TRUST MATRIX (Restored) ---
    st.divider()
    st.subheader("🤝 Diplomatic Trust Matrix")
    df_trust = pd.DataFrame(world.trust_matrix)
    # Sort columns and index for consistency
    df_trust = df_trust.sort_index().sort_index(axis=1)
    st.dataframe(df_trust.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=1), use_container_width=True)

elif st.session_state["active_tab"] == "LOGS":
    st.subheader("📜 Genesis History (Ancient)")
    with st.expander("View Genesis Events", expanded=False):
        for event in world.global_events:
            st.text(event)
            
    st.divider()
    
    st.subheader("🔄 Simulation Turn History")
    
    # Iterate over history in reverse (newest first)
    for i, turn_envelopes in enumerate(reversed(sim.history)):
        turn_num = len(sim.history) - i
        st.markdown(f"### Turn {turn_num}")
        
        for envelope in turn_envelopes:
            nation_name = world.nations[envelope.sender_id].name
            
            # Use expander for each nation's action
            with st.expander(f"{nation_name}: {envelope.public_statement}"):
                st.markdown(f"**Public Intent:** {envelope.public_intent.value}")
                st.markdown(f"**Global Strategy:** {envelope.global_strategy.value}")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**⚔️ Military**")
                    st.json(envelope.military_payload.model_dump()) 
                    st.caption(f"Intent: {envelope.military_intent.type.value}")
                with c2:
                    st.markdown("**💰 Economic**")
                    st.json(envelope.economic_payload.model_dump()) 
                    st.caption(f"Intent: {envelope.economic_intent.type.value}")
                with c3:
                    st.markdown("**🤝 Foreign**")
                    st.json(envelope.foreign_payload.model_dump()) 
                    st.caption(f"Intent: {envelope.foreign_intent.type.value}")

elif st.session_state["active_tab"] == "DECEPTION":
    st.subheader("Deception Analysis (Mock Data)")
    st.info("In a real run, this would show the Deception Score for each agent's last move.")
