"""
History & Logs Page.

Displays genesis events and simulation turn history.
"""

import streamlit as st
from typing import List
from geomas.schemas.world import WorldState
from geomas.agents.schemas import CountryEnvelope


def render_logs_page(world: WorldState, history: List[List[CountryEnvelope]]) -> None:
    """
    Renders the History & Logs tab content.
    
    Args:
        world: Current world state (for nation names)
        history: List of turn envelopes from simulation
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
                st.markdown(f"**Public Intent:** {envelope.public_intent.value}")
                st.markdown(f"**Global Strategy:** {envelope.global_strategy.value}")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**⚔️ Defense**")
                    st.json(envelope.defense_payload.model_dump())
                    st.caption(f"Intent: {envelope.defense_intent.type.value}")
                with c2:
                    st.markdown("**💰 Economic**")
                    st.json(envelope.economic_payload.model_dump())
                    st.caption(f"Intent: {envelope.economic_intent.type.value}")
                with c3:
                    st.markdown("**🤝 Foreign**")
                    st.json(envelope.foreign_payload.model_dump())
                    st.caption(f"Intent: {envelope.foreign_intent.type.value}")
