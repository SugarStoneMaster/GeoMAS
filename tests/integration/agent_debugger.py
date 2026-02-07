
import streamlit as st
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.world import generate_world
from geomas.agents.llm_client import LLMClient
from geomas.agents.ministers import ForeignMinister
from geomas.agents.context.memory import ContextManager
from geomas.agents.schemas import GlobalStrategy
from geomas.actions.common import Decision

# Import from our new integration test runner
# Be sure tests/integration is in path or use relative import if possible
try:
    from tests.integration.test_foreign_minister import (
        get_test_world,
        get_foreign_prompts,
        execute_foreign_agent
    )
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from tests.integration.test_foreign_minister import (
        get_test_world,
        get_foreign_prompts,
        execute_foreign_agent
    )

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="GeoMAS Agent Debugger",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 GeoMAS Agent Debugger")
st.markdown("Inspect prompts, modify inputs, and execute single agent calls.")

# --- SIDEBAR: CONFIG ---
with st.sidebar:
    st.header("Configuration")
    selected_agent = st.selectbox(
        "Select Agent to Test",
        ["Foreign Minister", "Economy Minister (TODO)", "Defense Minister (TODO)", "Opinion Agent (TODO)", "President (TODO)"]
    )
    
    st.subheader("LLM Settings")
    model_name = st.text_input("Model Name", value="azure/gpt-5-nano")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
    turn = st.number_input("Turn Number", min_value=1, value=1, step=1)
    
    if st.button("Reload World (Reset State)"):
        st.session_state.clear()
        st.rerun()

# --- STATE MANAGEMENT ---
if "world" not in st.session_state:
    with st.spinner("Generating simulated world..."):
        # Use common generator
        st.session_state.world = get_test_world(seed=42, n_nations=10)
        st.success("World generated!")

world = st.session_state.world
nation_ids = list(world.nations.keys())

# --- AGENT LOGIC ---

def render_foreign_minister():
    st.header("🌍 Foreign Minister Test")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Input Context")
        nation_id = st.selectbox("Select Nation", nation_ids, key="foreign_nation")

        
        # Strategy selection
        strategy_str = st.selectbox("Global Strategy", [s.value for s in GlobalStrategy], index=0)
        strategy = GlobalStrategy(strategy_str)
        
        st.markdown("### Scenario Editor")
        with st.expander("Modify Relationships (Optional)"):
            target_to_edit = st.selectbox("Select nation to edit relationship with:", [n for n in nation_ids if n != nation_id])
            
            # Interactive Relationship Context
            current_rel = world.relationship_matrix.get(nation_id, {}).get(target_to_edit, "NEUTRAL")
            rel_opts = ["WAR", "PEACE", "ALLIANCE", "NEUTRAL"]
            idx = rel_opts.index(current_rel) if current_rel in rel_opts else 3
            new_rel = st.selectbox(f"Relationship with {target_to_edit}", rel_opts, index=idx)
            
            # Update simulation state temporarily
            if nation_id not in world.relationship_matrix: world.relationship_matrix[nation_id] = {}
            world.relationship_matrix[nation_id][target_to_edit] = new_rel
            
            st.success(f"Set: {nation_id} <-> {target_to_edit} = {new_rel}")
        
        st.info(f"Testing as **{nation_id}** (Strategy: **{strategy.value}**)")

    # Generate Prompts using shared logic
    # Pass empty target_relationships dict because we updated world directly above
    system_prompt, user_prompt = get_foreign_prompts(
        world=world, 
        nation_id=nation_id, 
        strategy=strategy,
        turn=turn
    )

    with col2:
        st.subheader("📝 Prompt Preview")
        
        tab_sys, tab_user = st.tabs(["System Prompt", "User Prompt"])
        
        with tab_sys:
            st.markdown(f"```text\n{system_prompt}\n```")
            st.caption("Static instructions defining the persona and constraints.")
            
        with tab_user:
            st.markdown(f"```text\n{user_prompt}\n```")
            st.caption("Dynamic context injected at runtime.")

    # --- EXECUTION ---
    st.divider()
    if st.button("🚀 Execute Agent Request", type="primary"):
        with st.spinner("Calling LLM..."):
            try:
                # Use shared execution logic
                # We need to pass the same world object (already updated)
                # But execute_foreign_agent creates a new minister instance. That is fine.
                response, usage = execute_foreign_agent(
                    world=world,
                    nation_id=nation_id,
                    strategy=strategy,
                    turn=turn,
                    model_name=model_name,
                    temperature=temperature
                )
                
                st.subheader("✅ Agent Response")
                if usage:
                    st.success(f"Execution Successful | Tokens: {usage.total_tokens} ({usage.prompt_tokens} in / {usage.completion_tokens} out)")
                    if usage.reasoning_tokens:
                        st.info(f"🧠 Reasoning Tokens: {usage.reasoning_tokens}")
                else:
                    st.success("Execution Successful")
                
                # Visualizing result
                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    st.markdown("### Decision Breakdown")
                    st.write(f"**Intent Type:** `{response.intent.type.value}`")
                    st.write(f"**Reasoning:** {response.intent.reasoning}")
                    st.write(f"**Trust Impact:** {response.target_trust_impact}")
                
                with r_col2:
                    st.markdown("### Payload (Action)")
                    
                    decision_val = response.payload.decision.value
                    if decision_val == "PENDING":
                        st.warning(f"**Decision:** `{decision_val}` (Minister Proposal)")
                    else:
                        st.write(f"**Decision:** `{decision_val}`")
                    
                    if response.payload.action_type:
                        st.write(f"**Action:** `{response.payload.action_type.value}`")
                        
                        if response.payload.target_nation_id:
                            st.write(f"**Target Nation:** `{response.payload.target_nation_id}`")
                        
                        if response.payload.parameters:
                            st.write("**Parameters:**")
                            st.json(response.payload.parameters)
                        else:
                            st.write("**Parameters:** None")
                    else:
                        st.write("**Action:** `None` (Idle)")
                    
                    st.info("ℹ️ **Pydantic Validation:** The response above has been validated against the `ForeignProposal` schema.")

                st.markdown("### Raw JSON Response")
                st.json(response.model_dump())
                
            except Exception as e:
                st.error(f"Execution Failed: {str(e)}")
                st.exception(e)



# --- ROUTER ---
if selected_agent == "Foreign Minister":
    render_foreign_minister()
else:
    st.info("🚧 This agent is not yet implemented in the debugger.")
    st.warning("Please select 'Foreign Minister' to test.")

