import pytest
import sqlite3
import json
import os
from unittest.mock import MagicMock, patch
from geomas.db.connection import SimulationDB
from geomas.simulation.engine import SimulationEngine
from geomas.world import generate_world
from geomas.agents.schemas import CountryEnvelope
from tests.conftest import create_test_envelope

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_sim.duckdb"
    db = SimulationDB(str(db_file))
    db.initialize()
    yield db
    db.close()

class TestForkingAndInjections:
    
    def test_database_history_copy(self, temp_db):
        """Test SQL-level copying of history when forking."""
        # 1. Setup Source Simulation
        sim_id_1 = temp_db.create_simulation(42, 99, 100, 2, name="Source")
        
        # Insert dummy data for Turn 1 and 2
        for turn in [1, 2]:
            temp_db.save_snapshot(sim_id_1, turn, "{}", "{}", "{}", "{}", "{}", "{}")
            temp_db.save_envelope(sim_id_1, turn, "NATION_A", '{"payload": "test"}')
        
        # 2. Fork into Simulation 2 up to Turn 1
        sim_id_2 = temp_db.create_simulation(42, 99, 100, 2, name="Fork")
        temp_db.copy_history_for_fork(sim_id_1, sim_id_2, up_to_turn=1)
        
        # 3. Verify
        # Sim 2 should have Turn 1 data but NOT Turn 2
        snap_t1 = temp_db.load_snapshot(sim_id_2, 1)
        snap_t2 = temp_db.load_snapshot(sim_id_2, 2)
        
        assert snap_t1 is not None
        assert snap_t2 is None
        
        env_t1 = temp_db.load_envelopes(sim_id_2, 1)
        assert len(env_t1) == 1
        assert env_t1[0][0] == "NATION_A"
        
        info = temp_db.get_simulation_info(sim_id_2)
        assert info["total_turns"] == 1

    @patch("geomas.agents.nation_agent.NationAgent.act")
    def test_engine_fork_orchestration(self, mock_act, temp_db):
        """Test that SimulationEngine.fork() correctly migrates the engine state."""
        # Setup engine
        sim = SimulationEngine(map_seed=42, history_seed=99, n_cells=50, n_nations=2, db_path=temp_db.db_path)
        source_id = sim.simulation_id
        
        # Advance turn manually
        sim.world.turn = 5
        temp_db.save_snapshot(source_id, 5, "{}", "{}", "{}", "{}", "{}", "{}")
        
        # Fork
        new_id = sim.fork(new_name="Forked Sim")
        
        assert new_id != source_id
        assert sim.simulation_id == new_id
        assert sim.world.turn == 5
        
        # Verify new sim in DB
        info = temp_db.get_simulation_info(new_id)
        assert info["name"] == "Forked Sim"
        assert info["total_turns"] == 5
        
        sim.close()

    @patch("geomas.simulation.engine.run_opinion_phase")
    @patch("geomas.simulation.engine.run_upkeep_phase")
    @patch("geomas.agents.nation_agent.NationAgent.act")
    def test_injection_one_shot_pattern(self, mock_act, mock_upkeep, mock_opinion, temp_db):
        """
        Verify the one-shot injection pattern used in app.py.
        Ensures injections are cleared after a step.
        """
        sim = SimulationEngine(map_seed=42, history_seed=99, n_cells=50, n_nations=2, db_path=temp_db.db_path)
        
        # Mock agent action to return a valid envelope
        nation_id = list(sim.world.nations.keys())[0]
        mock_act.return_value = create_test_envelope(nation_id, turn=sim.world.turn)
        
        # Simulate UI state
        session_state = {
            "injections": [{"nation_id": nation_id, "role": "DEFENSE", "action": "STRIKE", "type": "FORCE"}],
            "remaining_turns": 5
        }
        
        # FIRST STEP (with injection)
        active_injections = session_state["injections"]
        sim.step(injections=active_injections)
        
        # Verify injection was passed
        mock_act.assert_called()
        # Find if any call had the injection
        # The engine calls agent.act(turn, injections)
        found_inj = False
        for call in mock_act.call_args_list:
            args, kwargs = call
            # Check args[1] or kwargs['injections']
            if len(args) > 1 and args[1] == active_injections:
                found_inj = True
            if kwargs.get("injections") == active_injections:
                found_inj = True
        
        assert found_inj, "Injections were not passed to agent.act"
        
        # CLEAR INJECTIONS (pattern from app.py)
        if active_injections:
            session_state["injections"] = []
            
        # SECOND STEP (should stay empty)
        mock_act.reset_mock()
        active_injections_2 = session_state["injections"]
        sim.step(injections=active_injections_2)
        
        assert len(active_injections_2) == 0
        for call in mock_act.call_args_list:
            args, kwargs = call
            inj_passed = kwargs.get("injections") or (args[1] if len(args) > 1 else None)
            assert not inj_passed, f"Injections were unexpectedly passed: {inj_passed}"
        
        sim.close()
