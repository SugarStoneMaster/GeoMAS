"""
Tests for Strategy-Aware System Prompt Updates.
Verifies that changing GlobalStrategy triggers prompt regeneration for Agents.
"""

import pytest
from unittest.mock import MagicMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.agents.nation_agent import NationAgent
from geomas.agents.ministers import DefenseMinister, EconomicMinister, ForeignMinister
from geomas.agents.schemas import GlobalStrategy, DefenseProposal, EconomicProposal, ForeignProposal, CabinetBriefing
from geomas.schemas.world import WorldState, NationState
from geomas.agents.llm_client import LLMClient
from geomas.agents.context.system.strategies import get_strategy_description

@pytest.fixture
def mock_client():
    client = MagicMock(spec=LLMClient)
    # Return dummy objects to avoid validation errors
    client.query_agent.return_value = MagicMock()
    return client

@pytest.fixture
def setup_agent(mock_client):
    nation = NationState(
        id="A", name="TestNation", color="#000", province_ids=[],
        total_budget=1000, total_materials=100, total_food=100, total_energy=100,
        total_population=1000, power_projection=50, public_satisfaction=50,
        cultural_traits=["Stoic"]
    )
    world = WorldState(turn=1, provinces={}, nations={"A": nation}, trust_matrix={})
    
    agent = NationAgent(
        nation_id="A", 
        world=world, 
        llm_client=mock_client,
        global_strategy=GlobalStrategy.TOTAL_EXPANSIONISM
    )
    return agent, world

def test_president_strategy_change(setup_agent, mock_client):
    """Verify President prompt updates when agent.strategy changes."""
    agent, world = setup_agent
    
    # 1. First Call: TOTAL_EXPANSIONISM
    mock_briefing = MagicMock()
    mock_briefing.defense = MagicMock(spec=DefenseProposal)
    mock_briefing.economy = MagicMock(spec=EconomicProposal)
    mock_briefing.foreign = MagicMock(spec=ForeignProposal)
    # Set dummy attributes to prevent downstream errors in summarize methods
    mock_briefing.defense.payload = MagicMock()
    mock_briefing.defense.payload.moves = []
    mock_briefing.defense.intent = MagicMock()
    mock_briefing.defense.intent.public_intent.value = "DETERRENCE"
    mock_briefing.defense.intent.private_intent.value = "DETERRENCE"
    mock_briefing.defense.intent.reasoning = "Test Reasoning"
    
    mock_briefing.economy.payload = MagicMock()
    mock_briefing.economy.payload.amount = 100.0
    mock_briefing.economy.payload.give_type = None
    mock_briefing.economy.payload.want_type = None
    mock_briefing.economy.intent = MagicMock()
    mock_briefing.economy.intent.public_intent.value = "GROWTH"
    mock_briefing.economy.intent.private_intent.value = "GROWTH"
    mock_briefing.economy.intent.reasoning = "Test Reasoning"
    
    mock_briefing.foreign.payload = MagicMock()
    mock_briefing.foreign.payload.target_nation_id = "B"
    mock_briefing.foreign.payload.diplomatic_message_type = None
    mock_briefing.foreign.payload.proposal_ref_type = None
    mock_briefing.foreign.intent = MagicMock()
    mock_briefing.foreign.intent.public_intent.value = "COOPERATION"
    mock_briefing.foreign.intent.private_intent.value = "COOPERATION"
    mock_briefing.foreign.intent.reasoning = "Test Reasoning"

    agent._presidential_decision(turn=1, briefing=mock_briefing)
    
    # Check arguments passed to query_agent
    args, _ = mock_client.query_agent.call_args
    system_prompt_1 = args[0]
    
    expansionist_desc = get_strategy_description(GlobalStrategy.TOTAL_EXPANSIONISM)
    assert expansionist_desc in system_prompt_1
    assert "TOTAL_EXPANSIONISM" in system_prompt_1
    
    # 2. Change Strategy: ARMED_ISOLATIONISM
    agent.strategy = GlobalStrategy.ARMED_ISOLATIONISM
    agent._presidential_decision(turn=1, briefing=mock_briefing)
    
    args, _ = mock_client.query_agent.call_args
    system_prompt_2 = args[0]
    
    isolationist_desc = get_strategy_description(GlobalStrategy.ARMED_ISOLATIONISM)
    assert isolationist_desc in system_prompt_2
    assert "ARMED_ISOLATIONISM" in system_prompt_2
    
    # Verify prompts are different
    assert system_prompt_1 != system_prompt_2


def test_defense_minister_strategy_change(setup_agent, mock_client):
    """Verify Defense Minister prompt updates when passed strategy changes."""
    agent, world = setup_agent
    minister = agent.defense_minister
    
    # 1. Propose with COALITION_BUILDER
    minister.propose(strategy=GlobalStrategy.COALITION_BUILDER, turn=1)
    
    args, _ = mock_client.query_agent.call_args
    prompt_1 = args[0]
    assert "COALITION_BUILDER" in prompt_1
    
    # 2. Propose with TOTAL_EXPANSIONISM
    minister.propose(strategy=GlobalStrategy.TOTAL_EXPANSIONISM, turn=1)
    
    args, _ = mock_client.query_agent.call_args
    prompt_2 = args[0]
    assert "TOTAL_EXPANSIONISM" in prompt_2
    
    assert prompt_1 != prompt_2

def test_economy_minister_strategy_change(setup_agent, mock_client):
    """Verify Economy Minister prompt updates."""
    agent, world = setup_agent
    minister = agent.economy_minister
    
    # 1. Propose with COALITION_BUILDER
    minister.propose(strategy=GlobalStrategy.COALITION_BUILDER, turn=1)
    prompt_1 = mock_client.query_agent.call_args[0][0]
    assert "COALITION_BUILDER" in prompt_1
    
    # 2. Propose with ARMED_ISOLATIONISM
    minister.propose(strategy=GlobalStrategy.ARMED_ISOLATIONISM, turn=1)
    prompt_2 = mock_client.query_agent.call_args[0][0]
    assert "ARMED_ISOLATIONISM" in prompt_2
    
    assert prompt_1 != prompt_2

def test_caching_efficiency(setup_agent, mock_client):
    """Verify that if strategy is same, cached prompt is reused (same object)."""
    agent, world = setup_agent
    
    # Force generation
    mock_briefing = MagicMock()
    mock_briefing.defense = MagicMock(spec=DefenseProposal)
    mock_briefing.economy = MagicMock(spec=EconomicProposal)
    mock_briefing.foreign = MagicMock(spec=ForeignProposal)
    mock_briefing.defense.payload = MagicMock()
    mock_briefing.defense.payload.moves = []
    mock_briefing.defense.intent = MagicMock()
    mock_briefing.defense.urgency = 5
    mock_briefing.defense.intent.public_intent.value = "DETERRENCE"
    mock_briefing.defense.intent.private_intent.value = "DETERRENCE"
    mock_briefing.defense.intent.reasoning = "Test Reasoning"
    
    mock_briefing.economy.payload = MagicMock()
    mock_briefing.economy.payload.amount = 100.0
    mock_briefing.economy.payload.give_type = None
    mock_briefing.economy.payload.want_type = None
    mock_briefing.economy.intent = MagicMock()
    mock_briefing.economy.intent.public_intent.value = "GROWTH"
    mock_briefing.economy.intent.private_intent.value = "GROWTH"
    mock_briefing.economy.intent.reasoning = "Test Reasoning"
    
    mock_briefing.foreign.payload = MagicMock()
    mock_briefing.foreign.payload.target_nation_id = "B"
    mock_briefing.foreign.payload.diplomatic_message_type = None
    mock_briefing.foreign.payload.proposal_ref_type = None
    mock_briefing.foreign.intent = MagicMock()
    mock_briefing.foreign.intent.public_intent.value = "COOPERATION"
    mock_briefing.foreign.intent.private_intent.value = "COOPERATION"
    mock_briefing.foreign.intent.reasoning = "Test Reasoning"

    agent._presidential_decision(turn=1, briefing=mock_briefing)
    cached_prompt = agent.president_system_prompt
    
    # Call again with same strategy
    agent._presidential_decision(turn=1, briefing=mock_briefing)
    
    # Should be identical object (str is immutable but if generated it might be new object with same content, 
    # but here we assign self.president_system_prompt)
    assert agent.president_system_prompt is cached_prompt
