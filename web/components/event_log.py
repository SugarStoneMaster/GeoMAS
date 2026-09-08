import streamlit as st
import pandas as pd
from typing import List
from geomas.agents.context.events.schemas import NotableEvent

def render_event_log(global_events: List[NotableEvent]):
    """
    Renders a table of global events from the ContextManager.
    """
    st.subheader("📜 Global Event Log")
    
    if not global_events:
        st.info("No global events recorded yet.")
        return

    # Convert NotableEvent objects to dicts for DataFrame
    events_data = []
    for event in global_events:
        events_data.append({
            "Turn": event.turn,
            "Type": event.event_type.value,
            "Description": event.summary,
            "Actors": ", ".join(event.actors) if event.actors else "Global"
        })

    df = pd.DataFrame(events_data)
    
    # Sort by Turn (descending) so newest events are top
    df = df.sort_values(by="Turn", ascending=False)
    
    st.dataframe(
        df, 
        width="stretch",
        column_config={
            "Turn": st.column_config.NumberColumn("Turn", format="%d"),
            "Type": "Event Type",
            "Description": "Content",
            "Actors": "Involved"
        },
        hide_index=True
    )
