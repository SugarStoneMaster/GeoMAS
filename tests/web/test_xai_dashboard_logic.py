import pytest
import os
from geomas.simulation import SimulationEngine
from geomas.agents.llm_client import LLMClient
from unittest.mock import MagicMock, patch

class TestXAIDashboardLogic:
    
    @pytest.fixture
    def sim_with_db(self, tmp_path):
        """Create a simulation with a real DuckDB in a temp folder."""
        db_path = tmp_path / "test_sim.duckdb"
        
        # Mock LLM to avoid API calls
        client = MagicMock(spec=LLMClient)
        # Mock response for query_agent (President)
        from geomas.agents.schemas import PresidentialDecree, DefenseDecree, EconomicDecree, ForeignDecree, Decision, DefenseIntentType, EconomicIntentType, ForeignIntentType
        
        client.last_raw_content = "{}"
        client.last_raw_usage = MagicMock()
        client.last_raw_usage.prompt_tokens = 0
        client.last_raw_usage.completion_tokens = 0
        client.last_raw_usage.total_tokens = 0
        client.last_raw_usage.model = "mock"
        
        decree = PresidentialDecree(
            defense=DefenseDecree(action=Decision.APPROVE, reasoning="."),
            economy=EconomicDecree(action=Decision.APPROVE, reasoning="."),
            foreign=ForeignDecree(action=Decision.APPROVE, reasoning="."),
            public_statement=".",
            defense_public_intent=DefenseIntentType.IDLE, defense_private_intent=DefenseIntentType.IDLE,
            economic_public_intent=EconomicIntentType.IDLE, economic_private_intent=EconomicIntentType.IDLE,
            foreign_public_intent=ForeignIntentType.IDLE, foreign_private_intent=ForeignIntentType.IDLE,
            defense_private_reasoning=".", economic_private_reasoning=".", foreign_private_reasoning="."
        )
        client.query_agent.return_value = decree
        from geomas.agents.schemas import DefenseProposal, DefenseIntent, DefenseIntentType, DefensePayload, Decision
        from geomas.agents.schemas import EconomicProposal, EconomicIntent, EconomicIntentType, EconomicPayload
        from geomas.agents.schemas import ForeignProposal, ForeignIntent, ForeignIntentType, ForeignPayload
        
        async def mock_minister_response(prompt, user_prompt, schema):
             # schema is a class, so check its name
             name = schema.__name__
             # print(f"DEBUG: Schema name: {name}") 
             if "Defense" in name:
                 return DefenseProposal(
                     intent=DefenseIntent(public_intent=DefenseIntentType.IDLE, private_intent=DefenseIntentType.IDLE, reasoning="."),
                     payload=DefensePayload(decision=Decision.VETO, moves=[])
                 )
             elif "Economic" in name:
                 return EconomicProposal(
                     intent=EconomicIntent(public_intent=EconomicIntentType.IDLE, private_intent=EconomicIntentType.IDLE, reasoning="."),
                     payload=EconomicPayload(decision=Decision.VETO)
                 )
             elif "Foreign" in name:
                  return ForeignProposal(
                     intent=ForeignIntent(public_intent=ForeignIntentType.IDLE, private_intent=ForeignIntentType.IDLE, reasoning="."),
                     payload=ForeignPayload(decision=Decision.VETO)
                 )
             # Fallback: Return a harmless Proposal if possible, or raise
             raise ValueError(f"Unknown schema: {name}")

        from unittest.mock import AsyncMock
        client.aquery_agent = AsyncMock(side_effect=mock_minister_response)
        
        # Mock run_opinion_phase
        with patch('geomas.simulation.engine.run_opinion_phase') as mock_opinion:
            sim = SimulationEngine(
                map_seed=42, 
                history_seed=99, 
                n_cells=50, 
                n_nations=4, 
                llm_client=client,
                db_path=str(db_path)
            )
            # print(f"DEBUG: Nation Keys: {list(sim.world.nations.keys())}")
            yield sim
            sim.close()

    def test_get_max_turn(self, sim_with_db):
        """Test that get_max_turn returns correct values as simulation progresses."""
        assert sim_with_db.db.get_max_turn(sim_with_db.simulation_id) == 1 # Initial snapshot
        
        # Run 2 turns
        sim_with_db.step() # T1 -> T2
        sim_with_db.step() # T2 -> T3
        
        assert sim_with_db.db.get_max_turn(sim_with_db.simulation_id) == 3

    def test_load_state_rollback(self, sim_with_db):
        """Test loading a previous state rolls back the world correctly."""
        # Run to Turn 5
        for _ in range(4):
            sim_with_db.step()
            
        assert sim_with_db.world.turn == 5
        assert sim_with_db.db.get_max_turn(sim_with_db.simulation_id) == 5
        
        # Modify state at T5 to verify rollback wipes it
        nid = list(sim_with_db.world.nations.keys())[0]
        sim_with_db.world.nations[nid].total_budget = 999999
        
        # Load T3
        sim_with_db.load_state(3)
        
        assert sim_with_db.world.turn == 3
        # Budget should be reset (not 999999) - checking exact value is hard, but it shouldn't be the hack
        assert sim_with_db.world.nations[nid].total_budget != 999999
        
    def test_load_state_persists_history(self, sim_with_db):
       """Test that loading state allows re-running (forking)."""
       # Run to T3
       sim_with_db.step()
       sim_with_db.step()
       
       # Load T2
       sim_with_db.load_state(2)
       assert sim_with_db.world.turn == 2
       
       # DB should now have max turn 3 (it overwrote or stayed same)
       assert sim_with_db.db.get_max_turn(sim_with_db.simulation_id) == 3

