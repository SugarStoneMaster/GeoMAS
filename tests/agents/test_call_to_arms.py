import pytest
import random
from geomas.schemas.world import WorldState, NationState, RelationshipState, ProvinceState, TerrainType
from geomas.actions.defense.schemas import DefensePayload, DefenseActionItem, DefenseActionType, UnitType
from geomas.simulation.engine import SimulationEngine
from geomas.actions import ActionEngine
from geomas.actions.common import Decision
from geomas.actions.defense.handler import execute_defense_waterfall
from geomas.agents.context.events import ContextManager
from geomas.agents.context.input.foreign import ForeignInputBuilder

def create_cta_scenario():
    # Setup a 3-nation world: A (Aggressor), B (Victim), C (Ally of B)
    w = WorldState(turn=1)
    
    # Nations
    w.nations["NAT_A"] = NationState(id="NAT_A", name="Aggressor", color="red")
    w.nations["NAT_B"] = NationState(id="NAT_B", name="Victim", color="blue")
    w.nations["NAT_C"] = NationState(id="NAT_C", name="Ally", color="green")
    
    # Provinces
    w.provinces[1] = ProvinceState(id=1, owner_id="NAT_A", terrain=TerrainType.LAND, coordinates=(0.0, 0.0), neighbors=[2])
    w.provinces[2] = ProvinceState(id=2, owner_id="NAT_B", terrain=TerrainType.LAND, coordinates=(1.0, 1.0), soldiers=10, neighbors=[1])
    w.nations["NAT_A"].province_ids = [1]
    w.nations["NAT_B"].province_ids = [2]
    
    # Relationships
    w.relationship_matrix = {
        "NAT_A": {"NAT_B": RelationshipState.PEACE, "NAT_C": RelationshipState.PEACE},
        "NAT_B": {"NAT_A": RelationshipState.PEACE, "NAT_C": RelationshipState.MUTUAL_DEFENSE},
        "NAT_C": {"NAT_A": RelationshipState.PEACE, "NAT_B": RelationshipState.MUTUAL_DEFENSE}
    }
    
    w.trust_matrix = {
        "NAT_A": {"NAT_B": 50.0, "NAT_C": 50.0},
        "NAT_B": {"NAT_A": 50.0, "NAT_C": 80.0},
        "NAT_C": {"NAT_A": 50.0, "NAT_B": 80.0}
    }
    
    # Resources for A to move
    w.nations["NAT_A"].total_energy = 100.0
    w.nations["NAT_A"].total_budget = 1000.0
    w.nations["NAT_A"].total_materials = 500.0
    
    # Engine
    sim = SimulationEngine(n_nations=3, map_seed=1, history_seed=1)
    sim.world = w
    sim.engine = ActionEngine(w)
    # Mock Agents dict (needed for iteration in _execute_global_betrayal)
    sim.agents = {"NAT_A": None, "NAT_B": None, "NAT_C": None}
    sim.context_manager = ContextManager()
    sim.context_manager.initialize_from_world(w)
    
    return sim, w

def test_sneak_attack_triggers_cta_for_ally():
    sim, w = create_cta_scenario()
    
    # 1. NAT_A sneak attacks NAT_B (Move troops into B's territory)
    # UnitType already imported above
    
    payload = DefensePayload(moves=[
        DefenseActionItem(
            priority=1,
            action_type=DefenseActionType.MOVE_TROOPS,
            unit_type=UnitType.SOLDIER,
            quantity=50,
            source_province_id=1,
            target_province_id=2,
            target_nation_id="NAT_B"
        )
    ], decision=Decision.APPROVE)
    
    # Inject units for A
    w.provinces[1].soldiers = 100
    w.nations["NAT_A"].total_soldiers = 100
    
    # Execute attack
    execute_defense_waterfall(sim.engine, "NAT_A", payload)
    
    # Verify Relationship set to WAR
    assert w.relationship_matrix["NAT_A"]["NAT_B"] == RelationshipState.WAR
    assert w.relationship_matrix["NAT_B"]["NAT_A"] == RelationshipState.WAR
    
    # Verify [CALL_TO_ARMS] event generated
    cta_events = [e for e in w.global_events if "[CALL_TO_ARMS]" in str(e)]
    assert len(cta_events) > 0
    assert "NAT_C" in str(cta_events[0])
    assert "SNEAK ATTACKED" in str(cta_events[0])

    # 2. Check NAT_C's prompt for the urgent CTA header
    sim.context_manager.update_after_turn(1, [], w)
    builder = ForeignInputBuilder(w)
    prompt = builder.build("NAT_C", turn=1, context_manager=sim.context_manager)
    
    assert "CRITICAL: CALL TO ARMS" in prompt
    assert "Your ally NAT_B was SNEAK ATTACKED by NAT_A" in prompt

def test_cta_3_turn_betrayal():
    sim, w = create_cta_scenario()
    
    # Setup immediate war status (simulate attack already happened)
    w.relationship_matrix["NAT_A"]["NAT_B"] = RelationshipState.WAR
    w.relationship_matrix["NAT_B"]["NAT_A"] = RelationshipState.WAR
    
    # NAT_C (Ally) is NOT at war with NAT_A
    assert w.relationship_matrix["NAT_C"]["NAT_A"] == RelationshipState.PEACE
    
    # Turn 1: Penalty 1/3
    sim._apply_ambiguity_penalty()
    assert w.nations["NAT_C"].betrayal_tracker.get("NAT_B", 0) == 1
    
    # Turn 2: Penalty 2/3
    sim._apply_ambiguity_penalty()
    assert w.nations["NAT_C"].betrayal_tracker["NAT_B"] == 2
    
    # Turn 3: BETRAYAL
    sim._apply_ambiguity_penalty()
    assert w.nations["NAT_C"].betrayal_tracker.get("NAT_B", 0) == 0
    assert w.relationship_matrix["NAT_C"]["NAT_B"] == RelationshipState.PEACE
    assert any("[BETRAYAL]" in e for e in sim.turn_logs)
    
    # Global Trust Penalty (-30)
    # Aggressor A also loses trust in the unreliable ally
    assert w.trust_matrix["NAT_A"]["NAT_C"] <= 20.0 # Started at 50

if __name__ == "__main__":
    pytest.main([__file__])
