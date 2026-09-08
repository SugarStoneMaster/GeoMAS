
import pytest
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas import GlobalStrategy

def test_ranked_profile_assignment():
    """
    Test that nations are assigned strategies based on their power ranking.
    High power -> Expansionism
    Low power -> Scorched Earth (in standard 4/6/8 configs)
    """
    # Use a specific seed known to produce variance or just test consistency
    engine = SimulationEngine(map_seed=42, n_nations=4)
    
    # 1. Get ranked nations by power
    # We duplicate the logic to verify
    ranked = sorted(
        engine.world.nations.keys(),
        key=lambda nid: (engine.world.nations[nid].power_projection, nid),
        reverse=True
    )
    
    # strongest = ranked[0]
    # weakest = ranked[-1]
    
    # 2. Check assigned strategies
    # For 4 nations, list is: Expansionism, Coalition, Isolationism, Scorched Earth
    assert engine.agents[ranked[0]].strategy == GlobalStrategy.TOTAL_EXPANSIONISM
    assert engine.agents[ranked[1]].strategy == GlobalStrategy.COALITION_BUILDER
    assert engine.agents[ranked[2]].strategy == GlobalStrategy.ARMED_ISOLATIONISM
    assert engine.agents[ranked[3]].strategy == GlobalStrategy.SCORCHED_EARTH
    
    print(f"Power Ranking: {[(n, engine.world.nations[n].power_projection) for n in ranked]}")
    for nid in ranked:
        print(f"Nation {nid}: Strategy {engine.agents[nid].strategy.value}")

def test_ranked_assignment_6_nations():
    engine = SimulationEngine(map_seed=123, n_nations=6)
    ranked = sorted(
        engine.world.nations.keys(),
        key=lambda nid: (engine.world.nations[nid].power_projection, nid),
        reverse=True
    )
    
    # Top 2 should be Expansionists based on setup_profiles[6]
    assert engine.agents[ranked[0]].strategy == GlobalStrategy.TOTAL_EXPANSIONISM
    assert engine.agents[ranked[1]].strategy == GlobalStrategy.TOTAL_EXPANSIONISM
    # Bottom should be Scorched Earth
    assert engine.agents[ranked[-1]].strategy == GlobalStrategy.SCORCHED_EARTH
    
if __name__ == "__main__":
    test_ranked_profile_assignment()
    test_ranked_assignment_6_nations()
