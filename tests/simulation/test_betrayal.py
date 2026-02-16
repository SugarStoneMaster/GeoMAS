import pytest
from geomas.schemas.world import WorldState, NationState, RelationshipState
from geomas.simulation.engine import SimulationEngine
from geomas.actions import ActionEngine

def create_mock_simulation():
    # 1. Create Engine (minimal init)
    sim = SimulationEngine(n_nations=4, map_seed=1, history_seed=1)
    
    # 2. Override World with our controlled state
    w = WorldState(turn=1)
    
    # Nations: A (Traitor), B (Victim), C (Aggressor), D (Observer)
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Nation A", color="blue")
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Nation B", color="red")
    w.nations["NAT_C"] = NationState(id="NAT_C", name="Nation C", color="green")
    w.nations["NAT_D"] = NationState(id="NAT_D", name="Nation D", color="yellow")
    
    # Initialize Matrices
    w.relationship_matrix = {}
    w.trust_matrix = {}
    
    for n1 in w.nations:
        w.relationship_matrix[n1] = {}
        w.trust_matrix[n1] = {}
        for n2 in w.nations:
            w.relationship_matrix[n1][n2] = RelationshipState.PEACE
            w.trust_matrix[n1][n2] = 50.0
            
    # Inject World into Simulation and ActionEngine
    sim.world = w
    sim.engine = ActionEngine(w)
    
    # Mock Agents dict (needed for iteration in _execute_global_betrayal)
    sim.agents = {"NAT_A": None, "NAT_B": None, "NAT_C": None, "NAT_D": None}
    
    return sim, w

def test_global_betrayal_trigger():
    sim, w = create_mock_simulation()
    
    # A & B are allies in MUTUAL_DEFENSE
    w.relationship_matrix["NAT_A"]["NAT_B"] = RelationshipState.MUTUAL_DEFENSE
    w.relationship_matrix["NAT_B"]["NAT_A"] = RelationshipState.MUTUAL_DEFENSE
    
    # B is at war with C
    w.relationship_matrix["NAT_B"]["NAT_C"] = RelationshipState.WAR
    w.relationship_matrix["NAT_C"]["NAT_B"] = RelationshipState.WAR
    
    # A trusts B (80)
    w.trust_matrix["NAT_B"]["NAT_A"] = 80.0
    
    # --- TURN 1 (Inertia 1/3) ---
    sim._apply_ambiguity_penalty()
    
    # NAT_A (Traitor) tracks their own betrayal of NAT_B
    assert w.nations["NAT_A"].betrayal_tracker.get("NAT_B", 0) == 1
    # Trust penalty (-2)
    assert w.trust_matrix["NAT_B"]["NAT_A"] == 78.0
    
    # --- TURN 2 (Inertia 2/3) ---
    sim._apply_ambiguity_penalty()
    assert w.nations["NAT_A"].betrayal_tracker["NAT_B"] == 2
    assert w.trust_matrix["NAT_B"]["NAT_A"] == 76.0
    
    # --- TURN 3 (Inertia 3/3 -> BETRAYAL) ---
    sim._apply_ambiguity_penalty()
    
    # 1. Tracker reset
    assert w.nations["NAT_A"].betrayal_tracker["NAT_B"] == 0
    
    # 2. Alliance Broken
    assert w.relationship_matrix["NAT_A"]["NAT_B"] == RelationshipState.PEACE
    assert w.relationship_matrix["NAT_B"]["NAT_A"] == RelationshipState.PEACE
    
    # 3. Massive Trust Hit for Victim (-50 hit)
    # 76 - 50 = 26.0
    assert w.trust_matrix["NAT_B"]["NAT_A"] == 26.0
    
    # 4. Global Trust Penalty (-30)
    # Observer D started at 50 -> should be 20
    assert w.trust_matrix["NAT_D"]["NAT_A"] == 20.0
    
    # 5. Global Event logged
    assert any("[BETRAYAL]" in e for e in sim.turn_logs)


def test_betrayal_tracker_reset_on_compliance():
    sim, w = create_mock_simulation()
    
    # Setup Conflict
    w.relationship_matrix["NAT_A"]["NAT_B"] = RelationshipState.MUTUAL_DEFENSE
    w.relationship_matrix["NAT_B"]["NAT_A"] = RelationshipState.MUTUAL_DEFENSE
    w.relationship_matrix["NAT_B"]["NAT_C"] = RelationshipState.WAR
    w.relationship_matrix["NAT_C"]["NAT_B"] = RelationshipState.WAR
    
    # Turn 1: A ignores -> Tracker = 1
    sim._apply_ambiguity_penalty()
    assert w.nations["NAT_A"].betrayal_tracker.get("NAT_B", 0) == 1
    
    # Turn 2: A declares war on C (Compliance)
    w.relationship_matrix["NAT_A"]["NAT_C"] = RelationshipState.WAR
    
    # Check again
    sim._apply_ambiguity_penalty()
    
    # Tracker should be reset to 0 because A is now helping
    assert w.nations["NAT_A"].betrayal_tracker.get("NAT_B", 0) == 0
