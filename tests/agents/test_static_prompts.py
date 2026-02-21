
import pytest
from unittest.mock import MagicMock, patch
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas import GlobalStrategy

def test_system_prompts_remain_static():
    """
    Verify that system prompts for President and all Ministers 
    remain exactly the same across multiple turns.
    """
    with patch("geomas.agents.llm_client.LLMClient") as MockClient:
        # Configure mock client to return dummy responses
        mock_client = MockClient.return_value
        mock_client.query_agent.return_value = MagicMock()
        mock_client.aquery_agent.return_value = MagicMock()
        
        # 1. Initialize engine
        engine = SimulationEngine(map_seed=42, n_nations=4)
        world = engine.world
        
        # Pick a nation to monitor
        nation_id = "AGRIA"
        agent = engine.agents[nation_id]
        
        # 2. Capture Turn 1 Prompts
        t1_president_prompt = agent.president_system_prompt
        t1_defense_prompt = agent.defense_minister.system_prompt
        t1_economy_prompt = agent.economy_minister.system_prompt
        t1_foreign_prompt = agent.foreign_minister.system_prompt
        
        assert t1_president_prompt is not None, "President prompt missing at T1"
        assert t1_defense_prompt is not None, "Defense prompt missing at T1"
        
        # 3. Simulate several turns
        for turn in range(2, 6):
            # Force a strategy change to try and trigger regeneration (if logic still existed)
            # note: even if agent.strategy is updated, the prompt should NOT change
            agent.strategy = GlobalStrategy.TOTAL_EXPANSIONISM if turn % 2 == 0 else GlobalStrategy.COALITION_BUILDER
            
            # Run agent act (with mocked client, this is fast)
            agent.act(turn)
            
            # 4. Compare with Turn 1
            assert agent.president_system_prompt == t1_president_prompt, f"President prompt changed at turn {turn}"
            assert agent.defense_minister.system_prompt == t1_defense_prompt, f"Defense prompt changed at turn {turn}"
            assert agent.economy_minister.system_prompt == t1_economy_prompt, f"Economy prompt changed at turn {turn}"
            assert agent.foreign_minister.system_prompt == t1_foreign_prompt, f"Foreign prompt changed at turn {turn}"

    print("✅ Static System Prompts Verification Passed!")

if __name__ == "__main__":
    test_system_prompts_remain_static()
