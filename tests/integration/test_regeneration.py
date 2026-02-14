
import os
import tempfile
import pytest
from unittest.mock import MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.agents.llm_client import LLMClient
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, 
    DefenseIntentType, EconomicIntentType, ForeignIntentType,
    DefensePayload, EconomicPayload, ForeignPayload
)

@pytest.fixture
def mock_act_response():
    def _mock(sender_id, turn):
        return CountryEnvelope(
            turn=turn,
            sender_id=sender_id,
            global_strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
            public_statement=f"Public statement for {sender_id} turn {turn}",
            defense_payload=DefensePayload(moves=[]),
            defense_public_intent=DefenseIntentType.DETERRENCE,
            defense_private_intent=DefenseIntentType.DETERRENCE,
            defense_private_reasoning="Defense reasoning",
            economic_payload=EconomicPayload(),
            economic_public_intent=EconomicIntentType.GROWTH,
            economic_private_intent=EconomicIntentType.GROWTH,
            economic_private_reasoning="Economic reasoning",
            foreign_payload=ForeignPayload(),
            foreign_public_intent=ForeignIntentType.COOPERATION,
            foreign_private_intent=ForeignIntentType.COOPERATION,
            foreign_private_reasoning="Foreign reasoning",
            last_system_prompt="System Prompt Content",
            last_input_prompt="User Prompt Content"
        )
    return _mock

def test_simulation_regeneration_roundtrip(mock_act_response):
    """
    Verifies that the simulation state (world, memory, and prompts) 
    can be perfectly restored from a database snapshot.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "regeneration.duckdb")
        
        # 1. Setup initial simulation
        mock_client = MagicMock(spec=LLMClient)
        engine = SimulationEngine(
            map_seed=42,
            history_seed=99,
            n_cells=100,
            n_nations=5,
            llm_client=mock_client,
            db_path=db_path
        )
        
        # Mock agents to avoid real LLM calls
        for n_id, agent in engine.agents.items():
            agent.act = MagicMock(side_effect=lambda turn, nid=n_id: mock_act_response(nid, turn))
            
        # Mock Opinion Agents
        for opinion_agent in engine.opinion_agents.values():
            mock_resp = MagicMock()
            mock_resp.multiplier_increase = 1.0
            mock_resp.multiplier_decrease = 1.0
            opinion_agent.react = MagicMock(return_value=mock_resp)

        # 2. Run turn 1
        engine.step()
        turn_to_restore = 2
        
        # Capture state before destruction
        original_turn = engine.world.turn # Should be 2 now
        original_nations = list(engine.world.nations.keys())
        original_memory = engine.context_manager.get_state()
        
        # Verify prompts were captured in the engine's history or DB
        envelopes = engine.db.load_envelopes(1)
        import json
        env_data = json.loads(envelopes[0][1])
        assert "last_system_prompt" in env_data
        assert env_data["last_system_prompt"] == "System Prompt Content"
        
        # 3. Create a NEW engine and load the state
        new_engine = SimulationEngine(
            map_seed=42,
            history_seed=99,
            n_cells=100,
            n_nations=5,
            llm_client=mock_client,
            db_path=db_path
        )
        
        new_engine.load_state(turn_to_restore)
        
        # 4. Assertions
        assert new_engine.world.turn == turn_to_restore
        assert list(new_engine.world.nations.keys()) == original_nations
        
        new_memory = new_engine.context_manager.get_state()
        assert len(new_memory["global_events"]) == len(original_memory["global_events"])
        assert new_memory["trust_history"] == original_memory["trust_history"]
        
        print("✅ State regeneration verified successfully.")

if __name__ == "__main__":
    # Allow running directly if needed
    pytest.main([__file__])
