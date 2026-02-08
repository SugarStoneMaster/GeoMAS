import streamlit as st
import json

def render_inspector(nation_id: str, agent_trace: dict):
    """
    Renders the Inspector Panel for a selected nation's agents.
    
    Args:
        nation_id: The ID of the selected nation.
        agent_trace: The 'last_trace' dictionary from the NationAgent.
    """
    if not agent_trace:
        st.warning("No trace data available for this turn yet.")
        return

    st.subheader(f"🕵️ Agent Inspector: {nation_id}")
    
    # Tabs for each agent role
    tabs = st.tabs(["President", "Defense", "Economy", "Foreign"])
    
    # helper to render a single agent's trace
    def _render_trace(trace_data, title):
        if not trace_data:
            st.info(f"No data for {title} this turn.")
            return
            
        with st.expander("📝 System Prompt", expanded=False):
            st.text_area("System Prompt", trace_data.get("system_prompt", ""), height=200, disabled=True)
            
        with st.expander("📥 User Prompt (Context)", expanded=False):
            st.text_area("User Prompt", trace_data.get("user_prompt", ""), height=200, disabled=True)
            
        with st.expander("📤 Output (JSON)", expanded=True):
            output = trace_data.get("proposal") or trace_data.get("decree")
            try:
                # Try to use model_dump_json if it's a Pydantic model
                if hasattr(output, 'model_dump_json'):
                    json_str = output.model_dump_json(indent=2)
                else:
                    # Fallback to string or dict dump
                    json_str = json.dumps(output, indent=2, default=str) if isinstance(output, (dict, list)) else str(output)
                
                st.code(json_str, language="json")
            except Exception as e:
                st.error(f"Could not render output: {e}")
                st.write(output)

    # 1. PRESIDENT TAB
    with tabs[0]:
        st.markdown("### 🏛️ President")
        _render_trace(agent_trace.get("president"), "President")

    # 2. DEFENSE TAB
    with tabs[1]:
        st.markdown("### 🛡️ Defense Minister")
        _render_trace(agent_trace.get("defense"), "Defense Minister")

    # 3. ECONOMY TAB
    with tabs[2]:
        st.markdown("### 💰 Economy Minister")
        _render_trace(agent_trace.get("economy"), "Economy Minister")

    # 4. FOREIGN TAB
    with tabs[3]:
        st.markdown("### 🤝 Foreign Minister")
        _render_trace(agent_trace.get("foreign"), "Foreign Minister")
