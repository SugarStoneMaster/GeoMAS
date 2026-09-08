import streamlit as st
import json
from geomas.agents.nation_agent import NationAgent

def render_inspector(nation_id: str, agent: NationAgent, opinion_agent=None):
    """
    Renders the Inspector Panel for a selected nation's agents.
    
    Args:
        nation_id: The ID of the selected nation.
        agent: The NationAgent instance.
        opinion_agent: Optional OpinionAgent instance.
    """
    history = getattr(agent, 'trace_history', {})
    
    if not history:
        st.warning("No trace data available yet.")
        return

    st.subheader(f"🕵️ Agent Inspector: {nation_id}")
    
    # Turn Selector
    available_turns = sorted(history.keys(), reverse=True)
    if not available_turns:
        st.info("No turns recorded.")
        return
        
    selected_turn = st.selectbox(
        "Select Turn to Inspect", 
        available_turns, 
        index=0,
        format_func=lambda t: f"Turn {t} {'(Latest)' if t == available_turns[0] else ''}"
    )
    
    agent_trace = history[selected_turn]
    
    # Tabs for each agent role (Public Opinion is now deterministic, no longer inspectable as LLM agent)
    tabs = st.tabs(["President", "Defense", "Economy", "Foreign"])
    
    # Helper for modal
    @st.dialog("Prompt Viewer", width="large")
    def show_prompt_modal(title: str, content: str):
        st.markdown(f"### {title}")
        lang = "json" if "JSON" in title or "Raw" in title else "markdown"
        st.code(content, language=lang)

    # helper to render a single agent's trace
    def _render_trace(trace_data, title):
        if not trace_data:
            st.info(f"No data for {title} this turn.")
            return
            
        c1, c2, c3 = st.columns(3)
        
        with c1:
            if st.button("📝 System Prompt", key=f"sys_{title}_{selected_turn}"):
                show_prompt_modal(f"{title} - System Prompt", trace_data.get("system_prompt", ""))
        
        with c2:
            if st.button("📥 User Prompt", key=f"user_{title}_{selected_turn}"):
                show_prompt_modal(f"{title} - User Prompt", trace_data.get("user_prompt", ""))
                
        with c3:
            if st.button("📤 Output (JSON)", key=f"out_{title}_{selected_turn}"):
                output = trace_data.get("proposal") or trace_data.get("decree")
                try:
                    if hasattr(output, 'model_dump_json'):
                        # Pydantic model: serialize with indentation
                        json_str = output.model_dump_json(indent=2)
                    elif isinstance(output, (dict, list)):
                        json_str = json.dumps(output, indent=2, default=str)
                    elif isinstance(output, str):
                        # Raw string from LLM: attempt to parse as JSON and re-pretty-print
                        try:
                            parsed = json.loads(output)
                            json_str = json.dumps(parsed, indent=2, ensure_ascii=False)
                        except json.JSONDecodeError:
                            json_str = output
                    else:
                        json_str = str(output)
                    
                    show_prompt_modal(f"{title} - Output", json_str)
                except Exception as e:
                    show_prompt_modal(f"{title} - Output Error", str(e))

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
