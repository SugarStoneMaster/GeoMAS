"""
Deception Analysis Page.

Displays deception scores for each nation based on their public vs private intents.
"""

import streamlit as st
from typing import List
from geomas.schemas.world import WorldState
from geomas.agents.schemas import CountryEnvelope
from geomas.analysis.deception import DeceptionAnalyzer


def render_deception_page(world: WorldState, history: List[List[CountryEnvelope]]) -> None:
    """
    Renders the Deception Analysis tab content.
    
    Analyzes the most recent turn's envelopes for deception scores.
    """
    st.subheader("🕵️ Deception Analysis")
    
    if not history:
        st.info("Run at least one turn to see deception analysis.")
        return
    
    # Get the most recent turn's envelopes
    latest_envelopes = history[-1]
    
    st.markdown("### Latest Turn Deception Scores")
    st.caption("Score: 0.0 = Honest, 1.0 = Maximum Deception")
    
    for envelope in latest_envelopes:
        nation = world.nations[envelope.sender_id]
        score = DeceptionAnalyzer.calculate_score(envelope)
        
        # Color code based on score
        if score < 0.3:
            color = "🟢"  # Honest
        elif score < 0.7:
            color = "🟡"  # Suspicious
        else:
            color = "🔴"  # Deceptive
        
        col1, col2, col3 = st.columns([2, 1, 3])
        col1.markdown(f"**{nation.name}**")
        col2.markdown(f"{color} **{score:.2f}**")
        col3.caption(f"Public: {envelope.public_intent.value} | Defense: {envelope.defense_intent.type.value}")
