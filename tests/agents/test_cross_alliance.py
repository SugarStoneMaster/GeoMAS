import pytest
from geomas.schemas.world import WorldState, NationState, RelationshipState, WarStats, ProvinceState, TerrainType
from geomas.simulation.engine import SimulationEngine
from geomas.actions import ActionEngine
from geomas.actions.foreign.handler import _execute_declare_war

def create_triangle_scenario():
    # Setup: A, B, C. B is allied with both A and C.
    w = WorldState(turn=1)
    
    # Nations
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Victim A", color="blue")
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Neutral B", color="green")
    w.nations["NAT_C"] = NationState(id="NAT_C", name="Aggressor C", color="red")
    
    # Initialize Matrices
    w.relationship_matrix = {
        "NAT_A": {"NAT_B": RelationshipState.MUTUAL_DEFENSE, "NAT_C": RelationshipState.PEACE},
        "NAT_B": {"NAT_A": RelationshipState.MUTUAL_DEFENSE, "NAT_C": RelationshipState.MUTUAL_DEFENSE},
        "NAT_C": {"NAT_A": RelationshipState.PEACE, "NAT_B": RelationshipState.MUTUAL_DEFENSE}
    }
    
    w.trust_matrix = {
        "NAT_A": {"NAT_B": 80.0, "NAT_C": 50.0},
        "NAT_B": {"NAT_A": 80.0, "NAT_C": 80.0},
        "NAT_C": {"NAT_A": 50.0, "NAT_B": 80.0}
    }
    
    # Engine
    sim = SimulationEngine(n_nations=3, map_seed=1, history_seed=1)
    sim.world = w
    sim.engine = ActionEngine(w)
    sim.agents = {"NAT_A": None, "NAT_B": None, "NAT_C": None}
    
    return sim, w

def test_aggressor_awareness_ambiguity_penalty():
    sim, w = create_triangle_scenario()
    
    # 1. C declares war on A (C is Aggressor, A is Victim)
    from geomas.actions.foreign.schemas import ForeignPayload, ForeignActionType
    # Manual call to handler logic (or mocked call)
    from geomas.actions.foreign.handler import _execute_declare_war
    
    _execute_declare_war(sim.engine, "NAT_C", "NAT_A", message="I want your land.")
    
    # Verify [CALL_TO_ARMS] and Dilemma Penalty
    # B should have lost trust in C because C attacked B's other ally A.
    assert w.trust_matrix["NAT_B"]["NAT_C"] == 65.0 # 80 - 15
    # B trust in A should remain stable
    assert w.trust_matrix["NAT_B"]["NAT_A"] == 80.0
    
    # Verify initiators in WarStats
    assert w.nations["NAT_C"].active_wars["NAT_A"].initiator_id == "NAT_C"
    assert w.nations["NAT_A"].active_wars["NAT_C"].initiator_id == "NAT_C"
    
    # 2. RUN Turn Processing Logic (_apply_ambiguity_penalty)
    # NAT_B is stay neutral.
    
    # Turn 1
    sim._apply_ambiguity_penalty()
    
    # NAT_B should track betrayal of NAT_A (Victim)
    assert w.nations["NAT_B"].betrayal_tracker.get("NAT_A", 0) == 1
    # NAT_B should NOT track betrayal of NAT_C (Aggressor)
    assert w.nations["NAT_B"].betrayal_tracker.get("NAT_C", 0) == 0
    
    # Trust from A (Victim) to B (Neutral) should decrease
    assert w.trust_matrix["NAT_A"]["NAT_B"] < 80.0
    # Trust from C (Aggressor) to B (Neutral) should NOT decrease (C can't expect help for aggression)
    assert w.trust_matrix["NAT_C"]["NAT_B"] == 80.0

def test_final_betrayal_is_selective():
    sim, w = create_triangle_scenario()
    
    # C attacks A
    _execute_declare_war(sim.engine, "NAT_C", "NAT_A")
    
    # Advance 3 turns of neutrality
    for _ in range(3):
        sim._apply_ambiguity_penalty()
        
    # VERIFY: B has betrayed A, but NOT C.
    # B-A Alliance should be broken
    assert w.relationship_matrix["NAT_A"]["NAT_B"] == RelationshipState.NON_AGGRESSION
    # B-C Alliance should remain (even if C is an aggressor, B didn't fail C)
    assert w.relationship_matrix["NAT_C"]["NAT_B"] == RelationshipState.MUTUAL_DEFENSE
    
    # Global Penalty: Traitor B should get hit globally for abandoning A
    # Observer A, C? Wait, C is an actor.
    # We should have a fourth nation for true "Observer" test, but let's check log.
    assert any("[BETRAYAL] NAT_B has abandoned NAT_A" in l for l in sim.turn_logs)
    assert not any("[BETRAYAL] NAT_B has abandoned NAT_C" in l for l in sim.turn_logs)

if __name__ == "__main__":
    pytest.main([__file__])
