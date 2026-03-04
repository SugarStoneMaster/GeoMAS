"""
Tests for the Regime Change Scenario.
"""
import pytest
from unittest.mock import patch, MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas.protocol import GovernmentType
from geomas.agents.schemas import GlobalStrategy
from geomas.agents.context.events.schemas import EventType, RelationshipSummary


@pytest.fixture
def temp_db(tmp_path):
    from geomas.db.connection import SimulationDB
    db_file = tmp_path / "test_regime.duckdb"
    db = SimulationDB(str(db_file))
    db.initialize()
    yield db
    db.close()

def setup_mocks(engine, target_id):
    """Helper to mock all agents in the engine."""
    from unittest.mock import patch, MagicMock
    
    # We need a function that returns a mock with the correct sender_id
    def mock_act(*args, **kwargs):
        # The agent being acted upon is 'self' which is args[0] if we patch the method
        # But we are using patch.object(a, 'act', ...) so it's simpler
        pass

    for aid, a in engine.agents.items():
        mock_env = MagicMock()
        mock_env.sender_id = aid
        mock_env.defense_payload = None
        mock_env.economic_payload = None
        mock_env.foreign_payload = None
        mock_env.public_statement = None
        patch.object(a, 'act', return_value=mock_env).start()

def test_trigger_regime_change(temp_db):
    """
    Simulates a running engine, triggers a REGIME_CHANGE scenario,
    and asserts that the NationAgent's state, memory, and prompts are properly updated.
    """
    with patch("geomas.agents.nation_agent.LLMClient") as MockClient:
        engine = SimulationEngine(
            map_seed=42, 
            history_seed=99, 
            n_cells=20, 
            n_nations=2, 
            db_path=temp_db.db_path
        )
        
        target_id = list(engine.agents.keys())[0]
        agent = engine.agents[target_id]
        agent.memory.append("ACTION PROPOSED: Build a tank.")
        agent.memory.append("ACTION EXECUTED: Tank constructed.")
        
        original_prompt = agent.president_system_prompt
        new_gov = GovernmentType.AUTHORITARIAN if agent.government_type != GovernmentType.AUTHORITARIAN else GovernmentType.DEMOCRACY
        new_strat = GlobalStrategy.TOTAL_EXPANSIONISM if agent.strategy != GlobalStrategy.TOTAL_EXPANSIONISM else GlobalStrategy.ARMED_ISOLATIONISM
        
        trigger = {
            "type": "REGIME_CHANGE",
            "turn": 1,
            "target_id": target_id,
            "new_gov": new_gov.value,
            "new_strategy": new_strat.value
        }
        
        setup_mocks(engine, target_id)
            
        with patch.object(engine, '_persist_envelopes'):
            engine.step(scenario_trigger=trigger)
        
        assert agent.government_type == new_gov
        assert agent.strategy == new_strat
        assert agent.president_system_prompt != original_prompt
        assert agent.defense_minister.government_type == new_gov
        
        for mem in agent.memory:
            assert mem.startswith("[Previous Government/Cabinet]")
            
        evts = [e for e in engine.context_manager.global_events if e.event_type == EventType.GLOBAL_SCENARIO]
        assert len(evts) >= 1
        assert "A new government has been formed" in evts[-1].summary
        
        evts = [e for e in engine.context_manager.global_events if e.event_type == EventType.REGIME_CHANGE and target_id in (e.relevance_to or [])]
        assert len(evts) >= 1
        assert new_strat.value in evts[-1].summary
        
        engine.close()

def test_regime_change_invalid_nation(temp_db):
    """
    Tests that an invalid target_id does not crash the engine and does not trigger events.
    """
    engine = SimulationEngine(
        map_seed=42, 
        history_seed=99, 
        n_cells=20, 
        n_nations=2, 
        db_path=temp_db.db_path
    )
    
    trigger = {
        "type": "REGIME_CHANGE",
        "turn": 1,
        "target_id": "NON_EXISTENT_ID",
        "new_gov": "DEMOCRACY",
        "new_strategy": "TOTAL_EXPANSIONISM"
    }
    
    setup_mocks(engine, None)
    
    with patch.object(engine, '_persist_envelopes'):
        engine.step(scenario_trigger=trigger)
    
    evts = [e for e in engine.context_manager.global_events if e.event_type == EventType.GLOBAL_SCENARIO]
    assert len(evts) == 0
    engine.close()

def test_regime_change_double_transition(temp_db):
    """
    Ensures that multiple consecutive regime changes tag memory correctly without double-tagging the prefix.
    """
    with patch("geomas.agents.nation_agent.LLMClient") as MockClient:
        engine = SimulationEngine(
            map_seed=42, 
            history_seed=99, 
            n_cells=20, 
            n_nations=2, 
            db_path=temp_db.db_path
        )
        target_id = list(engine.agents.keys())[0]
        agent = engine.agents[target_id]
        agent.memory.append("ORIGINAL ACTION")
        
        setup_mocks(engine, target_id)
            
        # 1. First trigger
        t1 = {
            "type": "REGIME_CHANGE",
            "turn": 1, "target_id": target_id, "new_gov": "AUTHORITARIAN", "new_strategy": "SCORCHED_EARTH"
        }
        with patch.object(engine, '_persist_envelopes'):
            engine.step(scenario_trigger=t1)
        
        assert "[Previous Government/Cabinet] ORIGINAL ACTION" in agent.memory
        
        # 2. Second trigger
        agent.memory.append("NEW REGIME ACTION")
        t2 = {
            "type": "REGIME_CHANGE",
            "turn": 2, "target_id": target_id, "new_gov": "DEMOCRACY", "new_strategy": "ARMED_ISOLATIONISM"
        }
        with patch.object(engine, '_persist_envelopes'):
            engine.step(scenario_trigger=t2)
        
        assert "[Previous Government/Cabinet] ORIGINAL ACTION" in agent.memory
        assert "[Previous Government/Cabinet] NEW REGIME ACTION" in agent.memory
        for mem in agent.memory:
            assert mem.count("[Previous Government/Cabinet]") == 1
            
        engine.close()

def test_regime_change_neutral_language(temp_db):
    """
    Verifies that the events generated do not use biased language like 'fallen' or 'regime'.
    """
    engine = SimulationEngine(
        map_seed=42, 
        history_seed=99, 
        n_cells=20, 
        n_nations=2, 
        db_path=temp_db.db_path
    )
    target_id = list(engine.agents.keys())[0]
    
    trigger = {
        "type": "REGIME_CHANGE",
        "turn": 1,
        "target_id": target_id,
        "new_gov": "DEMOCRACY",
        "new_strategy": "COALITION_BUILDER"
    }
    
    # Mocking
    setup_mocks(engine, target_id)
        
    with patch.object(engine, '_persist_envelopes'):
        engine.step(scenario_trigger=trigger)
        
    # Check Global Event
    global_evts = [e for e in engine.context_manager.global_events if e.event_type == EventType.GLOBAL_SCENARIO]
    assert "fallen" not in global_evts[-1].summary.lower()
    assert "regime" not in global_evts[-1].summary.lower()
    assert "new government has been formed" in global_evts[-1].summary
    
    # Check Private Event
    private_evts = [e for e in engine.context_manager.global_events if e.event_type == EventType.REGIME_CHANGE]
    assert "fallen" not in private_evts[-1].summary.lower()
    assert "government of" in private_evts[-1].summary.lower()
    assert "has changed" in private_evts[-1].summary.lower()
    
    engine.close()

def test_regime_change_opinion_sync(temp_db):
    """
    Verifies that the OpinionAgent's government_type is updated.
    """
    engine = SimulationEngine(
        map_seed=42, 
        history_seed=99, 
        n_cells=20, 
        n_nations=2, 
        db_path=temp_db.db_path
    )
    target_id = list(engine.agents.keys())[0]
    agent = engine.agents[target_id]
    
    new_gov = GovernmentType.THEOCRACY if agent.government_type != GovernmentType.THEOCRACY else GovernmentType.DEMOCRACY
    
    trigger = {
        "type": "REGIME_CHANGE",
        "turn": 1,
        "target_id": target_id,
        "new_gov": new_gov.value,
        "new_strategy": agent.strategy.value
    }
    
    # Mocking
    setup_mocks(engine, target_id)
        
    with patch.object(engine, '_persist_envelopes'):
        engine.step(scenario_trigger=trigger)
        
    # Verify OpinionAgent
    assert engine.opinion_agents[target_id].government_type == new_gov
    
    engine.close()
