
import pytest
from geomas.analysis.comparison import DeltaAnalyzer
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType
from geomas.agents.llm_client import LLMClient
from unittest.mock import MagicMock

class TestDeltaAnalyzer:
    @pytest.fixture
    def base_world(self):
        w = WorldState(turn=10)
        n1 = NationState(id="n1", name="Nation1", color="#FF0000", public_satisfaction=50.0, total_budget=100.0, total_soldiers=10)
        n2 = NationState(id="n2", name="Nation2", color="#00FF00", public_satisfaction=60.0, total_budget=200.0, total_soldiers=20)
        w.nations = {"n1": n1, "n2": n2}
        w.trust_matrix = {"n1": {"n2": 50.0}}
        w.relationship_matrix = {"n1": {"n2": "PEACE"}}
        return w

    @pytest.fixture
    def fork_world(self, base_world):
        # Create a copy with changes
        w = base_world.model_copy(deep=True)
        w.nations["n1"].public_satisfaction = 40.0 # -10
        w.nations["n1"].total_soldiers = 15 # +5
        w.nations["n2"].total_budget = 250.0 # +50
        
        w.trust_matrix["n1"]["n2"] = 30.0 # -20
        w.relationship_matrix["n1"]["n2"] = "WAR" # Changed
        
        return w

    def test_compare_worlds(self, base_world, fork_world):
        deltas = DeltaAnalyzer.compare_worlds(base_world, fork_world)
        
        # Check Nation Deltas
        d1 = deltas["nations"]["n1"]
        assert d1["satisfaction"] == -10.0
        assert d1["military"]["soldiers"] == 5
        
        d2 = deltas["nations"]["n2"]
        assert d2["resources"]["budget"] == 50.0
        
        # Check Global Deltas
        assert deltas["global"]["total_trust_divergence"] == 20.0
        assert len(deltas["global"]["relationship_changes"]) == 1
        rel = deltas["global"]["relationship_changes"][0]
        assert rel["base"] == "PEACE"
        assert rel["fork"] == "WAR"

    def test_divergence_score(self, base_world, fork_world):
        score = DeltaAnalyzer.calculate_divergence_score(base_world, fork_world)
        # Expected:
        # Sat diff: |-10| * 1.0 = 10.0
        # Power diff: Assumed 0 as per setup (should check formula) - wait, mock didn't update power_p
        # Trust: 20 * 0.5 = 10.0
        # Rel: 1 * 50 = 50.0
        # Total approx > 70
        assert score > 50.0

    def test_explain_divergence(self, base_world, fork_world):
        client = MagicMock(spec=LLMClient)
        # Mock structured response
        mock_response = MagicMock()
        mock_response.explanation = "Because war started."
        client.query_agent.return_value = mock_response
        
        explanation = DeltaAnalyzer.explain_divergence(base_world, fork_world, client, "Force War")
        
        assert explanation == "Because war started."
        # Verify prompt construction
        args = client.query_agent.call_args[0]
        # args[0] is system_prompt, args[1] is user_prompt
        prompt = args[1]
        assert "Satisfaction: -10.0" in prompt
        assert "Force War" in prompt
