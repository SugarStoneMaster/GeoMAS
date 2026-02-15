"""
Tests for Ministers.

Tests DefenseMinister, EconomicMinister, and ForeignMinister interactions.
Mocks the LLMClient to verify prompts and calls.
"""

from unittest.mock import MagicMock
import pytest
from geomas.world import generate_world
from geomas.agents.ministers import DefenseMinister, EconomicMinister, ForeignMinister
from geomas.agents.schemas import (
    GlobalStrategy, 
    DefenseProposal, 
    EconomicProposal, 
    ForeignProposal,
    DefenseIntent,
    EconomicIntent,
    ForeignIntent,
    DefenseIntentType,
    EconomicIntentType,
    ForeignIntentType,
    DefensePayload,
    EconomicPayload,
    ForeignPayload
)
from geomas.actions.economy.schemas import EconomicActionType
from geomas.actions.foreign.schemas import ForeignActionType
from geomas.actions.common import Decision
from geomas.agents.llm_client import LLMClient
from geomas.agents.context.events import ContextManager


class TestMinisterBase:
    """Base setup for minister tests."""
    
    @pytest.fixture
    def setup(self):
        """Create world, client mock, and nation."""
        world = generate_world(seed=42, n_cells=50, n_nations=1)
        nation_id = list(world.nations.keys())[0]
        
        client = MagicMock(spec=LLMClient)
        
        return world, nation_id, client


class TestDefenseMinister(TestMinisterBase):
    """Tests for Defense Minister."""
    
    def test_propose_calls_llm_correctly(self, setup):
        """Propose method calls client.query_agent with correct schema."""
        world, nation_id, client = setup
        minister = DefenseMinister(nation_id, world, client)
        
        # Mock response
        mock_response = DefenseProposal(
            intent=DefenseIntent(
                public_intent=DefenseIntentType.DEFENSE,
                private_intent=DefenseIntentType.DEFENSE,
                reasoning="Test reasoning"
            ),
            payload=DefensePayload(
                decision=Decision.APPROVE,
                moves=[]
            )
        )
        client.query_agent.return_value = mock_response
        
        strategy = GlobalStrategy.ARMED_ISOLATIONISM
        response = minister.propose(strategy, turn=1)
        
        # Verify call
        client.query_agent.assert_called_once()
        args, _ = client.query_agent.call_args
        system_prompt, user_prompt, schema = args
        
        assert "Defense Minister" in system_prompt
        assert issubclass(schema, DefenseProposal)
        assert response == mock_response
    
    def test_includes_memory_context(self, setup):
        """Includes recent actions in prompt if context manager is present."""
        world, nation_id, client = setup
        
        # Setup context manager with mock actions
        cm = MagicMock(spec=ContextManager)
        cm.get_actions_for.return_value = ["Action 1: Moved troops", "Action 2: Built fort"]
        cm.get_actions_for.return_value = ["Action 1: Moved troops", "Action 2: Built fort"]
        cm.get_events_for.return_value = []
        cm.get_presidential_feedback.return_value = ""
        
        minister = DefenseMinister(nation_id, world, client, context_manager=cm)
        
        # Mock response
        client.query_agent.return_value = DefenseProposal(
            intent=DefenseIntent(
                public_intent=DefenseIntentType.DEFENSE,
                private_intent=DefenseIntentType.DEFENSE,
                reasoning="Test"
            ),
            payload=DefensePayload(
                decision=Decision.APPROVE,
                moves=[]
            )
        )
        
        minister.propose(GlobalStrategy.ARMED_ISOLATIONISM, turn=1)
        
        # Check that context was requested
        cm.get_actions_for.assert_called_with(nation_id, domain="Defense", max_actions=8)
        
        # Check that prompt contains actions
        args, _ = client.query_agent.call_args
        user_prompt = args[1]
        assert "## Your history" in user_prompt
        assert "Action 1: Moved troops" in user_prompt
        assert "Moved troops" in user_prompt


class TestEconomicMinister(TestMinisterBase):
    """Tests for Economic Minister."""
    
    def test_propose_calls_llm_correctly(self, setup):
        """Propose method calls client.query_agent with correct schema."""
        world, nation_id, client = setup
        minister = EconomicMinister(nation_id, world, client)
        
        # Mock response
        mock_response = EconomicProposal(
            intent=EconomicIntent(
                public_intent=EconomicIntentType.GROWTH,
                private_intent=EconomicIntentType.GROWTH,
                reasoning="Test reasoning"
            ),
            payload=EconomicPayload(
                decision=Decision.APPROVE,
                action_type=EconomicActionType.INVEST_WELFARE,
                amount=10.0
            )
        )
        client.query_agent.return_value = mock_response
        
        strategy = GlobalStrategy.COALITION_BUILDER
        response = minister.propose(strategy, turn=1)
        
        # Verify call
        client.query_agent.assert_called_once()
        args, _ = client.query_agent.call_args
        system_prompt, user_prompt, schema = args
        
        assert "Economy Minister" in system_prompt
        assert schema == EconomicProposal
        assert response == mock_response
    
    def test_includes_memory_context(self, setup):
        """Includes history and world events in prompt."""
        world, nation_id, client = setup
        
        # Setup context manager with mock actions
        cm = MagicMock(spec=ContextManager)
        cm.get_actions_for.return_value = ["Welfare Boost"]
        cm.get_actions_for.return_value = ["Welfare Boost"]
        cm.get_events_for.return_value = []
        cm.get_presidential_feedback.return_value = ""
        
        minister = EconomicMinister(nation_id, world, client, context_manager=cm)
        
        # Mock response
        client.query_agent.return_value = EconomicProposal(
            intent=EconomicIntent(
                public_intent=EconomicIntentType.IDLE,
                private_intent=EconomicIntentType.IDLE,
                reasoning="Test"
            ),
            payload=EconomicPayload(decision=Decision.APPROVE, action_type=None),
            projected_cost=0.0
        )
        
        minister.propose(GlobalStrategy.COALITION_BUILDER, turn=1)
        
        # Check prompt
        args, _ = client.query_agent.call_args
        user_prompt = args[1]
        
        assert "## Your history" in user_prompt
        assert "Welfare Boost" in user_prompt


class TestForeignMinister(TestMinisterBase):
    """Tests for Foreign Minister."""
    
    def test_propose_calls_llm_correctly(self, setup):
        """Propose method calls client.query_agent with correct schema."""
        world, nation_id, client = setup
        minister = ForeignMinister(nation_id, world, client)
        
        # Mock response
        mock_response = ForeignProposal(
            intent=ForeignIntent(
                public_intent=ForeignIntentType.COOPERATION,
                private_intent=ForeignIntentType.COOPERATION,
                reasoning="Test reasoning"
            ),
            payload=ForeignPayload(
                decision=Decision.APPROVE,
                action_type=ForeignActionType.PROPOSE_ALLIANCE,
                target_nation_id="NationB"
            )
        )
        client.query_agent.return_value = mock_response
        
        strategy = GlobalStrategy.COALITION_BUILDER
        response = minister.propose(strategy, turn=1)
        
        # Verify call
        client.query_agent.assert_called_once()
        args, _ = client.query_agent.call_args
        system_prompt, user_prompt, schema = args
        
        assert "Foreign Minister" in system_prompt
        assert schema == ForeignProposal
        assert response == mock_response
    
    def test_includes_memory_context(self, setup):
        """Includes history and world events in prompt."""
        world, nation_id, client = setup
        
        # Setup context manager with mock actions
        cm = MagicMock(spec=ContextManager)
        cm.get_actions_for.return_value = ["Test Action"]
        cm.get_actions_for.return_value = ["Test Action"]
        cm.get_events_for.return_value = []
        cm.get_presidential_feedback.return_value = ""
        cm.global_events = []
        
        minister = ForeignMinister(nation_id, world, client, context_manager=cm)
        
        # Mock response
        client.query_agent.return_value = ForeignProposal(
            intent=ForeignIntent(
                public_intent=ForeignIntentType.IDLE,
                private_intent=ForeignIntentType.IDLE,
                reasoning="Test"
            ),
            payload=ForeignPayload(
                decision=Decision.APPROVE,
                action_type=None,
                target_nation_id=None
            )
        )
        
        minister.propose(GlobalStrategy.COALITION_BUILDER, turn=1)
        
        # Check prompt
        args, _ = client.query_agent.call_args
        user_prompt = args[1]
        
        assert "## Your history" in user_prompt
        assert "Test Action" in user_prompt
