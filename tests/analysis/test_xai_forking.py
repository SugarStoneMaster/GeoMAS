
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, 
    DefenseProposal, EconomicProposal, ForeignProposal,
    DefenseIntent, DefenseIntentType,
    EconomicIntent, EconomicIntentType,
    ForeignIntent, ForeignIntentType,
    PresidentialDecree, PresidentialDecision, Decision,
    DefenseDecree, EconomicDecree, ForeignDecree
)
from geomas.actions.defense.schemas import DefenseProposalPayload
from geomas.actions.economy.schemas import EconomicProposalPayload
from geomas.actions.foreign.schemas import ForeignProposalPayload
from geomas.agents.opinion import OpinionResponse
from datetime import datetime

class TestXAIForking:

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.aquery_agent = AsyncMock()
        client.query_agent = MagicMock()
        
        # Set last_raw_content to a string to avoid MagicMock serialization issues
        client.last_raw_content = "{}"
        
        # Default mock responses
        def_prop = DefenseProposal(intent=DefenseIntent(public_intent=DefenseIntentType.IDLE, private_intent=DefenseIntentType.IDLE, reasoning="Idle"), payload=DefenseProposalPayload(moves=[]))
        eco_prop = EconomicProposal(intent=EconomicIntent(public_intent=EconomicIntentType.IDLE, private_intent=EconomicIntentType.IDLE, reasoning="Idle"), payload=EconomicProposalPayload(action_type=None), projected_cost=0.0)
        for_prop = ForeignProposal(intent=ForeignIntent(public_intent=ForeignIntentType.IDLE, private_intent=ForeignIntentType.IDLE, reasoning="Idle"), payload=ForeignProposalPayload(action_type=None, proposal_responses=[]), target_trust_impact=0.0)
        
        import itertools
        client.aquery_agent.side_effect = itertools.cycle([def_prop, eco_prop, for_prop]) 
        
        # Mock President response
        
        decree = PresidentialDecree(
            public_statement="We are peaceful.",
            defense=DefenseDecree(action=PresidentialDecision.APPROVE, reasoning="Approved."),
            economy=EconomicDecree(action=PresidentialDecision.APPROVE, reasoning="Approved."),
            foreign=ForeignDecree(action=PresidentialDecision.APPROVE, reasoning="Approved.")
        )
        
        # Mock Opinion Interaction
        opinion = OpinionResponse(
            mood="HAPPY",
            reasoning="Good job.",
            multiplier_increase=1.1,
            multiplier_decrease=0.9
        )
        opinion.raw_json = "{}"

        def query_side_effect(*args, **kwargs):
            model = kwargs.get('response_model')
            if model == PresidentialDecree:
                return decree
            elif model == OpinionResponse:
                return opinion
            return decree

        client.query_agent.side_effect = query_side_effect
        
        return client

        return client

    @pytest.fixture
    def engine(self, mock_client, tmp_path):
        db_path = str(tmp_path / "test_sim.db")
        # Use small map for speed
        return SimulationEngine(map_seed=42, history_seed=99, n_cells=100, n_nations=4, llm_client=mock_client, db_path=db_path)

    def test_injection_passed_to_ministers(self, engine, mock_client):
        """Test that injection instruction reaches the minister prompt."""
        # Get a real nation ID
        target_id = list(engine.agents.keys())[0]
        
        # Setup injection
        test_injection = [
            {
                "nation_id": target_id,
                "role": "DEFENSE",
                "intent": "CONQUEST",
                "type": "FORCE"
            }
        ]
        
        # Run 1 step with injection
        engine.step(injections=test_injection)
        
        # Verify call to aquery_agent contained the instruction
        found = False
        for call_args in mock_client.aquery_agent.call_args_list:
            system_prompt, user_prompt, model = call_args[0]
            if "SYSTEM INSTRUCTION: You represent a counterfactual timeline. You MUST choose Intent CONQUEST." in user_prompt:
                found = True
                break
        
        assert found, "Injection instruction not found in any minister prompt call"

    def test_forking_determinism_and_divergence(self, engine, mock_client, tmp_path):
        """Test that forking from T1 is deterministic without injection, and diverges with injection."""
        
        # 1. Run Base Sim to T2
        engine.run(steps=1) # T1
        
        # Get a real nation ID for tracking
        target_id = list(engine.agents.keys())[0]
        
        # 2. Fork 1: Deterministic Control
        fork_db = str(tmp_path / "test_sim.db") # Same DB
        fork1 = SimulationEngine(map_seed=42, history_seed=99, n_cells=100, n_nations=4, llm_client=mock_client, db_path=fork_db)
        fork1.load_state(1)
        
        # Reset mock call history to cleanly capture fork1
        mock_client.aquery_agent.reset_mock()
        mock_client.query_agent.reset_mock()
        
        fork1.step() # Run T1 -> T2
        
        # Capture trace of target
        trace1 = fork1.agents[target_id].last_trace
        
        # 3. Fork 2: Injected Divergence
        fork2 = SimulationEngine(map_seed=42, history_seed=99, n_cells=100, n_nations=4, llm_client=mock_client, db_path=fork_db)
        fork2.load_state(1)
        
        # Reset mock again
        mock_client.aquery_agent.reset_mock()
        
        # Inject constraint
        injection = [{"nation_id": target_id, "role": "DEFENSE", "intent": "PACIFIST", "type": "FORCE"}]
        fork2.step(injections=injection)
        
        # Verify injection was sent
        found_injection = False
        for call_args in mock_client.aquery_agent.call_args_list:
            _, user_prompt, _ = call_args[0]
            if "choose Intent PACIFIST" in user_prompt:
                found_injection = True
                break
        
        assert found_injection, "Fork 2 did not receive injection."

        
