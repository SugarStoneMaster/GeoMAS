
import pytest
import os
import shutil
from geomas.db import SimulationDB
from geomas.simulation import SimulationEngine
from geomas.agents.llm_client import LLMClient
from unittest.mock import MagicMock

DB_PATH = "tests/data/test_multi_sim.duckdb"

@pytest.fixture
def clean_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    # Ensure dir exists
    os.makedirs("tests/data", exist_ok=True)
    yield DB_PATH
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_simulation_id_increment(clean_db):
    """Test that simulation IDs increment correctly."""
    db = SimulationDB(clean_db)
    db.initialize()
    
    id1 = db.create_simulation(1, 1, 100, "Sim 1")
    assert id1 == 1
    
    id2 = db.create_simulation(2, 2, 100, "Sim 2")
    assert id2 == 2
    
    sims = db.get_simulations()
    assert len(sims) == 2
    assert sims[0]['id'] == 2  # Ordered DESC
    assert sims[1]['id'] == 1

def test_engine_auto_id(clean_db):
    """Test that Engine auto-creates IDs."""
    # Sim 1
    engine1 = SimulationEngine(db_path=clean_db, n_nations=4, n_cells=100)
    assert engine1.simulation_id == 1
    engine1.close()
    
    # Sim 2
    engine2 = SimulationEngine(db_path=clean_db, n_nations=4, n_cells=100)
    assert engine2.simulation_id == 2
    engine2.close()
    
    # Reload Sim 1
    engine1_reload = SimulationEngine(db_path=clean_db, simulation_id=1, n_nations=4, n_cells=100)
    # Checks
    assert engine1_reload.simulation_id == 1
    engine1_reload.close()

def test_data_isolation(clean_db):
    """Test that data is isolated between simulations."""
    # Run Sim 1 for 1 turn
    engine1 = SimulationEngine(db_path=clean_db, n_nations=4, n_cells=100) 
    # Mock act to avoid LLM calls
    for agent in engine1.agents.values():
        agent.act = MagicMock(return_value=MagicMock(sender_id=agent.id, global_strategy=agent.strategy))
    
    # We need to mock execution to avoid side effects? 
    # Actually engine.step() does a lot.
    # Let's just manually save data to DB to simulate a run safely.
    
    db = engine1.db
    # Save Sim 1 Turn 5
    db.save_snapshot(1, 5, "{}", "{}", "{}", "{}", "{}", '{}') 
    
    # Create Sim 2
    id2 = db.create_simulation(1, 1, 100)
    # Save Sim 2 Turn 5
    db.save_snapshot(id2, 5, "{\"sim\": 2}", "{}", "{}", "{}", "{}", '{}')
    
    # Verify Load
    snap1 = db.load_snapshot(1, 5)
    snap2 = db.load_snapshot(2, 5)
    
    assert snap1['provinces_json'] == "{}"
    assert snap2['provinces_json'] == "{\"sim\": 2}"
    
    # Verify data leakage
    assert db.load_snapshot(1, 6) is None
