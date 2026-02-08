import streamlit as st
import pandas as pd

def render_event_log(history: list):
    """
    Renders a table of global events from the simulation history.
    """
    st.subheader("📜 Global Event Log")
    
    if not history:
        st.info("No events recorded yet.")
        return

    # Flatten events from history envelopes
    events = []
    for turn_data in history: 
        # structure of history depends on engine implementation
        # usually list of dicts: {nid: Envelope}
        if not turn_data: continue
        
        turn_num = list(turn_data.values())[0].turn if turn_data else "?"
        
        for nid, envelope in turn_data.items():
            if not envelope: continue
            
            # Extract public statement
            if envelope.public_statement:
                events.append({
                    "Turn": turn_num,
                    "Nation": nid,
                    "Type": "STATEMENT",
                    "Content": envelope.public_statement
                })
                
            # Extract specific actions if needed (e.g. War declarations)
            # This requires parsing the envelope payload or reading from ContextManager global_events
            # For now, we use public statements which summarize the turn for other agents.

    if not events:
        st.info("No public events found.")
        return

    df = pd.DataFrame(events)
    # Sort by Turn (descending)
    df = df.sort_values(by="Turn", ascending=False)
    
    st.dataframe(
        df, 
        use_container_width=True,
        column_config={
            "Turn": st.column_config.NumberColumn("Turn", format="%d"),
            "Nation": "Actor",
            "Type": "Event Type",
            "Content": "Description"
        },
        hide_index=True
    )
