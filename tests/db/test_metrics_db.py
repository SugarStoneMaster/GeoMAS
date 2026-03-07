"""
Tests for the Metrics Database and Telemetry extraction logic.
"""

import pytest
import os
import duckdb
from geomas.simulation.engine import SimulationEngine
from geomas.db.metrics_db import MetricsDB

@pytest.fixture
def temp_metrics_db(tmp_path):
    """Creates a temporary metrics database path."""
    db_path = str(tmp_path / "test_metrics.duckdb")
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def temp_sim_db(tmp_path):
    """Creates a temporary simulation database path."""
    db_path = str(tmp_path / "test_sim.duckdb")
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

def test_metrics_db_creation(temp_metrics_db):
    """Test that MetricsDB initializes and creates the correct tables."""
    db = MetricsDB(temp_metrics_db)
    
    # Check tables exist
    tables = db.conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    
    assert "metrics_nation" in table_names
    assert "metrics_global" in table_names
    assert "metrics_trust" in table_names
    
    db.close()

def test_simulation_engine_creates_metrics_db(temp_sim_db):
    """Test that SimulationEngine automatically creates a linked metrics DB."""
    # We use a mocked LLM client to skip actual generation
    from unittest.mock import MagicMock
    mock_client = MagicMock()
    
    engine = SimulationEngine(
        db_path=temp_sim_db, 
        n_nations=4, 
        llm_client=mock_client
    )
    
    assert engine.metrics_db is not None
    
    # Check if the file was created with the correct suffix
    expected_metrics_path = temp_sim_db.replace(".duckdb", "_metrics.duckdb")
    assert os.path.exists(expected_metrics_path)
    
    # We patch run_upkeep_phase to throw an exception to halt execution
    # but let's test a full cycle by mocking the agent.act directly.
    
    from geomas.agents.schemas.protocol import (
        CountryEnvelope, GlobalStrategy, GovernmentType, DefensePayload, 
        EconomicPayload, ForeignPayload, DefenseIntentType, ForeignIntentType
    )
    
    def fake_act(turn, injections=None):
        return CountryEnvelope(
            turn=turn,
            sender_id="OSTER",
            global_strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
            government_type=GovernmentType.DEMOCRACY.value,
            public_statement="Peace and prosperity.",
            
            defense_payload=DefensePayload(),
            defense_public_intent=DefenseIntentType.DEFENSE,
            defense_private_intent=DefenseIntentType.CONQUEST, # Mismatch -> Deception!
            defense_private_reasoning="Fake reasoning",
            
            economic_payload=EconomicPayload(),
            economic_private_reasoning="Fake reasoning",
            
            foreign_payload=ForeignPayload(),
            foreign_public_intent=ForeignIntentType.COOPERATION,
            foreign_private_intent=ForeignIntentType.COOPERATION,
            foreign_private_reasoning="Fake reasoning"
        )
        
    for agent in engine.agents.values():
        agent.act = fake_act
        
    # Run 1 step, bypassing complex phases that would fail on our mocked setup
    from unittest.mock import patch
    
    with patch('geomas.simulation.engine.run_upkeep_phase'), \
         patch('geomas.simulation.engine.run_opinion_phase'), \
         patch.object(engine, '_persist_token_usage'):
         
        engine.step()
    
    # Verify Metrics DB was populated
    conn = duckdb.connect(expected_metrics_path)
    
    # 1. Check Nations
    nations_df = conn.execute("SELECT * FROM metrics_nation WHERE turn = 1").df()
    assert len(nations_df) == 4
    
    # Verify Deception Calculation (Private=CONQUEST but Public=DEFENSE + says 'Peace')
    # Should trigger both mismatch penalty(0.5) and semantic penalty(0.5), clamped to 1.0
    oster_row = nations_df[nations_df['nation_id'] == 'OSTER'].iloc[0]
    assert oster_row['deception_defense'] == 1.0
    assert oster_row['deception_foreign'] == 0.0 # Match
    
    # 2. Check Global
    global_df = conn.execute("SELECT * FROM metrics_global WHERE turn = 1").df()
    assert len(global_df) == 1
    
    # 3. Check Trust
    trust_df = conn.execute("SELECT * FROM metrics_trust WHERE turn = 1").df()
    # 4 nations -> 4x4 relationships = 16 edges (including self)
    assert len(trust_df) == 16
    
    conn.close()
    engine.close()
