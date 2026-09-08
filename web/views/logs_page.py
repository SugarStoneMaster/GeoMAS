"""
History & Logs Page.

Displays genesis events and simulation turn history.
"""

import streamlit as st
from typing import List
from geomas.schemas.world import WorldState
from geomas.agents.schemas import CountryEnvelope


from geomas.agents.context.events.schemas import NotableEvent


def render_logs_page(world: WorldState, history: List[List[CountryEnvelope]], global_events: List[NotableEvent] = None) -> None:
    """
    Renders the History & Logs tab content.
    
    Args:
        world: Current world state (for nation names)
        history: List of turn envelopes from simulation
        global_events: List of notable events from ContextManager
    """
    # Genesis events (only shown when GENESIS_ENABLED=true)
    import os
    if os.environ.get("GENESIS_ENABLED", "false").lower() == "true":
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
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**⚔️ Defense**")
                    st.caption(f"Public: {envelope.defense_public_intent.value}")
                    st.caption(f"Private: {envelope.defense_private_intent.value}")
                    if envelope.defense_payload:
                        st.json(envelope.defense_payload.model_dump())
                with c2:
                    st.markdown("**💰 Economic**")
                    if envelope.economic_payload:
                        st.json(envelope.economic_payload.model_dump())
                with c3:
                    st.markdown("**🤝 Foreign**")
                    st.caption(f"Public: {envelope.foreign_public_intent.value}")
                    st.caption(f"Private: {envelope.foreign_private_intent.value}")
                    if envelope.foreign_payload:
                        st.json(envelope.foreign_payload.model_dump())

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
                        st.markdown("**📋 Satisfaction**")
                        mood = getattr(envelope, "opinion_mood", None)
                        inc = getattr(envelope, "opinion_multiplier_increase", 0)
                        dec = getattr(envelope, "opinion_multiplier_decrease", 0)
                        reasoning = getattr(envelope, "opinion_reasoning", "No data.")
                        if mood:
                            st.info(f"**Mood:** {mood}")
                        if inc or dec:
                            st.caption(f"📈 +{inc:.2f} | 📉 -{dec:.2f}")
                        st.caption(reasoning)
