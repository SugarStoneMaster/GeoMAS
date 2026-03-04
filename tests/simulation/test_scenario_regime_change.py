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
        
        # Select target nation
        target_id = list(engine.agents.keys())[0]
        agent = engine.agents[target_id]
        
        # Populate some memory to ensure it gets tagged later
        agent.memory.append("ACTION PROPOSED: Build a tank.")
        agent.memory.append("ACTION EXECUTED: Tank constructed.")
        
        # Original state
        original_gov = agent.government_type
        original_strat = agent.strategy
        original_prompt = agent.president_system_prompt
        
        # Define trigger at turn 1
        new_gov = GovernmentType.AUTHORITARIAN if original_gov != GovernmentType.AUTHORITARIAN else GovernmentType.DEMOCRACY
        new_strat = GlobalStrategy.TOTAL_EXPANSIONISM if original_strat != GlobalStrategy.TOTAL_EXPANSIONISM else GlobalStrategy.ARMED_ISOLATIONISM
        
        trigger = {
            "type": "REGIME_CHANGE",
            "turn": 1,
            "target_id": target_id,
            "new_gov": new_gov.value,
            "new_strategy": new_strat.value
        }
        
        # Step the engine (this processes the scenario at the start of the turn)
        # Mock agent.act to prevent LLM execution
        mock_env = MagicMock()
        mock_env.sender_id = target_id
        mock_env.defense_payload = None
        mock_env.economic_payload = None
        mock_env.foreign_payload = None
        mock_env.public_statement = None
        
        with patch.object(agent, 'act', return_value=mock_env):
            # Mock the other agent too
            other_id = list(engine.agents.keys())[1]
            mock_env_other = MagicMock()
            mock_env_other.sender_id = other_id
            mock_env_other.defense_payload = None
            mock_env_other.economic_payload = None
            mock_env_other.foreign_payload = None
            mock_env_other.public_statement = None
            
            with patch.object(engine.agents[other_id], 'act', return_value=mock_env_other):
                # Mock persistence to avoid serialization of MagicMock
                with patch.object(engine, '_persist_envelopes'):
                    engine.step(scenario_trigger=trigger)
        
        # 1. Assert NationAgent state changed
        assert agent.government_type == new_gov
        assert agent.strategy == new_strat
        assert agent.president_system_prompt != original_prompt
        
        # 2. Assert Ministers changed
        assert agent.defense_minister.government_type == new_gov
        assert agent.defense_minister.strategy == new_strat
        
        # 3. Assert Memory was tagged correctly
        for mem in agent.memory:
            assert mem.startswith("[Previous Government/Cabinet]")
            
        # 4. Assert World Event was generated
        evts = [e for e in engine.context_manager.global_events if e.event_type == EventType.GLOBAL_SCENARIO]
        assert len(evts) >= 1
        assert "A new government has been formed" in evts[-1].summary
        
        # 5. Assert Private Directive Event was generated
        evts = [e for e in engine.context_manager.global_events if e.event_type == EventType.REGIME_CHANGE and target_id in (e.relevance_to or [])]
        assert len(evts) >= 1
        assert new_strat.value in evts[-1].summary
        
        engine.close()
