"""
Alliances & Diplomatic Status Panel.

Displays a summary of all active diplomatic relationships:
Mutual Defense alliances, Non-Aggression Pacts, active wars, and neutral/peace pairs.
"""

import streamlit as st
from geomas.schemas.world import WorldState, RelationshipState


def render_alliances_panel(world: WorldState) -> None:
    """
    Renders a summary of all active diplomatic relationships grouped by status.

    Groups are:
    - War: pairs currently at war
    - Mutual Defense: active military alliances
    - Non-Aggression: active NAPs
    - Peace/Neutral: all other pairs (collapsed by default)
    """
    st.subheader("⚔️ Diplomatic Status")

    matrix = world.relationship_matrix
    nation_ids = list(world.nations.keys())

    wars: list[tuple[str, str]] = []
    mutual_defense: list[tuple[str, str]] = []
    non_aggression: list[tuple[str, str]] = []
    peace: list[tuple[str, str]] = []

    # Collect unique ordered pairs (A < B alphabetically to avoid duplicates)
    seen: set[frozenset[str]] = set()
    for a in nation_ids:
        for b in nation_ids:
            if a == b:
                continue
            pair_key = frozenset({a, b})
            if pair_key in seen:
                continue
            seen.add(pair_key)

            # Relationship is symmetric by design; read from A->B direction
            rel = matrix.get(a, {}).get(b, RelationshipState.PEACE)

            a_name = world.nations[a].name
            b_name = world.nations[b].name

            if rel == RelationshipState.WAR:
                wars.append((a_name, b_name))
            elif rel == RelationshipState.MUTUAL_DEFENSE:
                mutual_defense.append((a_name, b_name))
            elif rel == RelationshipState.NON_AGGRESSION:
                non_aggression.append((a_name, b_name))
            else:
                peace.append((a_name, b_name))

    # --- WARS ---
    if wars:
        st.markdown("**🔴 At War**")
        for a, b in wars:
            st.error(f"⚔️ {a} vs {b}", icon=None)
    else:
        st.markdown("**🔴 At War**")
        st.caption("No active wars.")

    # --- MUTUAL DEFENSE ---
    st.markdown("**🔵 Mutual Defense**")
    if mutual_defense:
        for a, b in mutual_defense:
            st.success(f"🛡️ {a} — {b}", icon=None)
    else:
        st.caption("No active alliances.")

    # --- NON-AGGRESSION ---
    st.markdown("**🟡 Non-Aggression Pacts**")
    if non_aggression:
        for a, b in non_aggression:
            st.info(f"🤝 {a} — {b}", icon=None)
    else:
        st.caption("No active pacts.")

    # --- PEACE / NEUTRAL (collapsed) ---
    with st.expander(f"🟢 Peace / Neutral ({len(peace)} pairs)", expanded=False):
        if peace:
            for a, b in peace:
                st.caption(f"✌️ {a} — {b}")
        else:
            st.caption("No neutral pairs.")
