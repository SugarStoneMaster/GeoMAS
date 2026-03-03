"""
Tests for the engine telemetry metrics extraction.
"""

import pytest
from unittest.mock import MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType
from geomas.agents.context.events.schemas import EventType

@pytest.fixture
def mock_sim_engine():
    engine = SimulationEngine()
    engine.simulation_id = "test_sim_id"
    class FakeDB:
        def __init__(self):
            self.mock_calls = []
        def insert_nation_metrics(self, *args): self.mock_calls.append(("insert_nation", args))
        def insert_global_metrics(self, *args): self.mock_calls.append(("insert_global", args))
        def insert_trust_metrics(self, *args): self.mock_calls.append(("insert_trust", args))
        def insert_action_outcomes(self, *args): self.mock_calls.append(("insert_action", args))
        def insert_presidential_decisions(self, *args): self.mock_calls.append(("insert_pres", args))

    engine.metrics_db = FakeDB()
    engine.db = MagicMock()
    
    # Create dummy world state
    world = WorldState()
    nation = NationState(
        id="N1", name="Nation 1", color="red", total_population=1000,
        province_ids=[1]
    )
    world.nations["N1"] = nation
    
    engine.world = world
    return engine

def test_engine_telemetry_extraction(mock_sim_engine, monkeypatch):
    """
    Test that the engine correctly parses TERRITORY_LOST and COMBAT_RESULT 
    events from the world log into the global KPI dictionary.
    """
    engine = mock_sim_engine
    
    # Create a dummy envelope using MagicMock
    dummy_env = MagicMock()
    dummy_env.sender_id = "N1"
    dummy_env.public_statement = "Peace and prosperity"
    dummy_env.defense_private_intent = "DEFENSE"
    dummy_env.defense_public_intent = "DEFENSE"
    dummy_env.foreign_private_intent = "COOPERATION"
    dummy_env.global_strategy = MagicMock(value="COALITION_BUILDER")
    dummy_env.government_type = "DEMOCRACY"
    
    # Mock defense payload with moves simulating combat outcomes
    move1 = MagicMock()
    move1.action_type.value = "MOVE_TROOPS"
    move1.unit_type.value = "SOLDIER"
    move1.execution_outcome.status = "SUCCESS"
    move1.execution_outcome.details = {
        "attacker_wins": True,
        "attacker_losses": 100,
        "defender_losses": 200
    }
    
    move2 = MagicMock()
    move2.action_type.value = "MOVE_TROOPS"
    move2.unit_type.value = "NAVY"
    move2.execution_outcome.status = "SUCCESS"
    move2.execution_outcome.details = {
        "attacker_wins": True,
        "attacker_losses_navy": 50,
        "defender_losses": 150
    }
    
    move3 = MagicMock()
    move3.action_type.value = "MOVE_TROOPS"
    move3.unit_type.value = "AIRCRAFT"
    move3.execution_outcome.status = "SUCCESS"
    move3.execution_outcome.details = {
        "attacker_wins": True, # Air strikes win but don't conquer land
        "attacker_losses": 20,
        "defender_losses": 30
    }
    
    dummy_env.defense_payload.moves = [move1, move2, move3]
    
    # Mock serialization so it doesn't crash on MagicMock
    monkeypatch.setattr("geomas.simulation.engine.serialize_envelope", lambda env: "{}")
    
    # Manually invoke the telemetry block usually inside _persist_envelopes
    engine._persist_envelopes(5, [dummy_env])
    
    # Find the global_metrics call
    global_call = next((c for c in engine.metrics_db.mock_calls if c[0] == "insert_global"), None)
    assert global_call is not None, f"Global metrics were not inserted! Calls: {engine.metrics_db.mock_calls}"
    
    args = global_call[1]
    # args: (simulation_id, turn, global_data)
    assert args[0] == "test_sim_id"
    assert args[1] == 5
    
    global_data = args[2]
    
    # Should be 2 territories lost for turn 5
    assert global_data["territories_changed_hands"] == 2
    
    # Should sum 200 + 350 = 550 from "lost 200" and "lost 350"
    assert global_data["units_destroyed"] == 550
    

