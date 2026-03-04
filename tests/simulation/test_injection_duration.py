"""
Tests for multi-turn XAI injections in SimulationEngine.run().
"""
import pytest
from unittest.mock import MagicMock
from geomas.simulation.engine import SimulationEngine


@pytest.fixture
def minimal_engine(tmp_path):
    from geomas.db.connection import SimulationDB
    db_file = tmp_path / "test_inj.duckdb"
    db = SimulationDB(str(db_file))
    db.initialize()

    # Mock everything not related to the engine loop
    engine = SimulationEngine(map_seed=42, history_seed=99, n_cells=10, n_nations=2, db_path=str(db_file))
    engine.step = MagicMock()
    return engine


def test_injection_default_duration(minimal_engine):
    """If no duration is provided, it defaults to 1 and applies for 1 step only."""
    injections = [{"nation_id": "N1", "role": "DEFENSE", "action": "STRIKE", "type": "FORCE"}]
    
    # Run for 3 steps
    minimal_engine.run(steps=3, injections=injections)
    
    assert minimal_engine.step.call_count == 3
    
    # Step 1 should receive the injection with duration 1
    call_1 = minimal_engine.step.call_args_list[0]
    injs_passed_1 = call_1.kwargs.get("injections")
    assert injs_passed_1 is not None
    assert len(injs_passed_1) == 1
    assert injs_passed_1[0]["duration"] == 1
    
    # Step 2 should receive None
    call_2 = minimal_engine.step.call_args_list[1]
    assert call_2.kwargs.get("injections") is None
    
    # Step 3 should receive None
    call_3 = minimal_engine.step.call_args_list[2]
    assert call_3.kwargs.get("injections") is None


def test_injection_multi_turn_duration(minimal_engine):
    """If duration is N, it applies for N steps and decrement each step."""
    injections = [{"nation_id": "N2", "duration": 2, "action": "TRADE"}]
    
    # Run for 4 steps
    minimal_engine.run(steps=4, injections=injections)
    
    assert minimal_engine.step.call_count == 4
    
    # Step 1
    call_1 = minimal_engine.step.call_args_list[0]
    injs_1 = call_1.kwargs.get("injections")
    assert len(injs_1) == 1
    assert injs_1[0]["duration"] == 2
    
    # Step 2
    call_2 = minimal_engine.step.call_args_list[1]
    injs_2 = call_2.kwargs.get("injections")
    assert len(injs_2) == 1
    assert injs_2[0]["duration"] == 1
    
    # Step 3
    call_3 = minimal_engine.step.call_args_list[2]
    assert call_3.kwargs.get("injections") is None
    
    # Step 4
    call_4 = minimal_engine.step.call_args_list[3]
    assert call_4.kwargs.get("injections") is None


def test_mixed_durations(minimal_engine):
    """Tests multiple injections with different duration expirations."""
    injections = [
        {"id": 1, "duration": 1},
        {"id": 2, "duration": 3},
        {"id": 3} # defaults to 1
    ]
    
    minimal_engine.run(steps=4, injections=injections)
    
    # Step 1 checks
    injs_1 = minimal_engine.step.call_args_list[0].kwargs.get("injections")
    assert len(injs_1) == 3
    assert {i["id"] for i in injs_1} == {1, 2, 3}
    
    # Step 2 checks (id 1 and 3 should drop)
    injs_2 = minimal_engine.step.call_args_list[1].kwargs.get("injections")
    assert len(injs_2) == 1
    assert injs_2[0]["id"] == 2
    assert injs_2[0]["duration"] == 2
    
    # Step 3 checks
    injs_3 = minimal_engine.step.call_args_list[2].kwargs.get("injections")
    assert len(injs_3) == 1
    assert injs_3[0]["id"] == 2
    assert injs_3[0]["duration"] == 1
    
    # Step 4 checks (all expired)
    injs_4 = minimal_engine.step.call_args_list[3].kwargs.get("injections")
    assert injs_4 is None
