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
                
                c1, c2, c3 = st.columns(3)
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
