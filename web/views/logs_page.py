"""
History & Logs Page.

Displays genesis events and simulation turn history.
"""

import streamlit as st
from typing import List
from geomas.schemas.world import WorldState
from geomas.agents.schemas import CountryEnvelope


from geomas.agents.context.memory.schemas import NotableEvent

def render_logs_page(world: WorldState, history: List[List[CountryEnvelope]], global_events: List[NotableEvent] = None) -> None:
    """
    Renders the History & Logs tab content.
    
    Args:
        world: Current world state (for nation names)
        history: List of turn envelopes from simulation
        global_events: List of notable events from ContextManager
    """
    # Genesis events
    st.subheader("📜 Genesis History (Ancient)")
    with st.expander("View Genesis Events", expanded=False):
        for event in world.global_events:
            st.text(event)
    
    st.divider()
    
    # Simulation turn history
    st.subheader("🔄 Simulation Turn History")
    
    # Iterate in reverse (newest first)
    for i, turn_envelopes in enumerate(reversed(history)):
        turn_num = len(history) - i
        st.markdown(f"### Turn {turn_num}")
        
        for envelope in turn_envelopes:
            nation_name = world.nations[envelope.sender_id].name
            
            with st.expander(f"{nation_name}: {envelope.public_statement}"):
                st.markdown(f"**Global Strategy:** {envelope.global_strategy.value}")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown("**⚔️ Defense**")
                    st.caption(f"Public: {envelope.defense_public_intent.value}")
                    st.caption(f"Private: {envelope.defense_private_intent.value}")
                    if envelope.defense_payload:
                        st.json(envelope.defense_payload.model_dump())
                with c2:
                    st.markdown("**💰 Economic**")
                    st.caption(f"Public: {envelope.economic_public_intent.value}")
                    st.caption(f"Private: {envelope.economic_private_intent.value}")
                    if envelope.economic_payload:
                        st.json(envelope.economic_payload.model_dump())
                with c3:
                    st.markdown("**🤝 Foreign**")
                    st.caption(f"Public: {envelope.foreign_public_intent.value}")
                    st.caption(f"Private: {envelope.foreign_private_intent.value}")
                    if envelope.foreign_payload:
                        st.json(envelope.foreign_payload.model_dump())
                with c4:
                    st.markdown("**👥 Opinion**")
                    mood = getattr(envelope, "opinion_mood", "Unknown")
                    st.info(f"**Mood:** {mood}")
                    reasoning = getattr(envelope, "opinion_reasoning", "No reasoning recorded.")
                    st.caption(reasoning)
                    
                    # Trend indicators
                    inc = getattr(envelope, "opinion_multiplier_increase", 0)
                    dec = getattr(envelope, "opinion_multiplier_decrease", 0)
                    if inc or dec:
                        st.caption(f"📈 +{inc:.2f} | 📉 -{dec:.2f}")

                # --- TRACEABILITY & XAI ---
                with st.expander("🔍 Prompts & Raw Traces (XAI)"):
                    trace_cols = st.columns(3)
                    
                    with trace_cols[0]:
                        st.markdown("**President**")
                        if st.checkbox("System Prompt", key=f"sys_p_{turn_num}_{envelope.sender_id}"):
                            st.code(envelope.last_system_prompt)
                        if st.checkbox("User Prompt", key=f"usr_p_{turn_num}_{envelope.sender_id}"):
                            st.code(envelope.last_input_prompt)
                        if st.checkbox("Raw Output", key=f"raw_p_{turn_num}_{envelope.sender_id}"):
                            st.code(envelope.raw_president_response or "Empty")

                    with trace_cols[1]:
                        agent_trace = st.selectbox(
                            "Select Minister", 
                            ["Defense", "Economic", "Foreign"],
                            key=f"agent_sel_{turn_num}_{envelope.sender_id}"
                        )
                        if agent_trace == "Defense":
                            sys, usr, raw = envelope.defense_system_prompt, envelope.defense_input_prompt, envelope.raw_defense_response
                        elif agent_trace == "Economic":
                            sys, usr, raw = envelope.economic_system_prompt, envelope.economic_input_prompt, envelope.raw_economic_response
                        else:
                            sys, usr, raw = envelope.foreign_system_prompt, envelope.foreign_input_prompt, envelope.raw_foreign_response
                            
                        if st.checkbox(f"{agent_trace} System", key=f"sys_m_{turn_num}_{envelope.sender_id}"):
                            st.code(sys or "None")
                        if st.checkbox(f"{agent_trace} User", key=f"usr_m_{turn_num}_{envelope.sender_id}"):
                            st.code(usr or "None")
                        if st.checkbox(f"{agent_trace} Raw JSON", key=f"raw_m_{turn_num}_{envelope.sender_id}"):
                            st.code(raw or "Empty")

                    with trace_cols[2]:
                        st.markdown("**Public Opinion**")
                        if st.checkbox("Opinion System", key=f"sys_o_{turn_num}_{envelope.sender_id}"):
                            st.code(getattr(envelope, "opinion_system_prompt", "None"))
                        if st.checkbox("Opinion User", key=f"usr_o_{turn_num}_{envelope.sender_id}"):
                            st.code(getattr(envelope, "opinion_input_prompt", "None"))
                        if st.checkbox("Opinion Raw Output", key=f"raw_o_{turn_num}_{envelope.sender_id}"):
                            st.code(getattr(envelope, "raw_opinion_response", "Empty"))
