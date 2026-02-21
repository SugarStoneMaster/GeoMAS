"""
Tests for Static System Prompts (Strategy-Immune).
Verifies that changing GlobalStrategy does NOT trigger prompt regeneration for Agents.
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

def test_president_prompt_is_static_after_strategy_change(setup_agent, mock_client):
    """Verify President prompt remains the same even if agent.strategy changes."""
    agent, world = setup_agent
    
    # 1. First Call: TOTAL_EXPANSIONISM
    mock_briefing = MagicMock()
    mock_briefing.defense = MagicMock(spec=DefenseProposal)
    mock_briefing.economy = MagicMock(spec=EconomicProposal)
    mock_briefing.foreign = MagicMock(spec=ForeignProposal)
    mock_briefing.defense.payload = MagicMock(); mock_briefing.defense.payload.moves = []
    mock_briefing.defense.intent = MagicMock(); mock_briefing.defense.intent.public_intent.value = "DETERRENCE"
    mock_briefing.defense.intent.private_intent.value = "DETERRENCE"
    mock_briefing.defense.intent.reasoning = "Test"
    
    mock_briefing.economy.payload = MagicMock(); mock_briefing.economy.payload.amount = 100.0
    mock_briefing.economy.payload.give_type = None; mock_briefing.economy.payload.want_type = None
    mock_briefing.economy.intent = MagicMock(); mock_briefing.economy.intent.public_intent.value = "GROWTH"
    mock_briefing.economy.intent.private_intent.value = "GROWTH"
    mock_briefing.economy.intent.reasoning = "Test"
    
    mock_briefing.foreign.payload = MagicMock(); mock_briefing.foreign.payload.target_nation_id = "B"
    mock_briefing.foreign.payload.diplomatic_message_type = None; mock_briefing.foreign.payload.proposal_ref_type = None
    mock_briefing.foreign.intent = MagicMock(); mock_briefing.foreign.intent.public_intent.value = "COOPERATION"
    mock_briefing.foreign.intent.private_intent.value = "COOPERATION"
    mock_briefing.foreign.intent.reasoning = "Test"

    agent._presidential_decision(turn=1, briefing=mock_briefing)
    prompt_1 = mock_client.query_agent.call_args[0][0]
    cached_prompt = agent.president_system_prompt
    
    # 2. Change Strategy: ARMED_ISOLATIONISM
    agent.strategy = GlobalStrategy.ARMED_ISOLATIONISM
    agent._presidential_decision(turn=2, briefing=mock_briefing)
    
    prompt_2 = mock_client.query_agent.call_args[0][0]
    
    # Verify prompts are IDENTICAL
    assert prompt_1 == prompt_2
    assert agent.president_system_prompt == cached_prompt
    assert "TOTAL_EXPANSIONISM" in prompt_2
    assert "ARMED_ISOLATIONISM" not in prompt_2 # Should NOT be updated

def test_defense_minister_prompt_remains_static(setup_agent, mock_client):
    """Verify Defense Minister prompt doesn't update when passed strategy differs from init."""
    agent, _ = setup_agent
    minister = agent.defense_minister
    
    # 1. Propose with its current strategy (TOTAL_EXPANSIONISM from setup)
    minister.propose(strategy=GlobalStrategy.TOTAL_EXPANSIONISM, turn=1)
    prompt_1 = mock_client.query_agent.call_args[0][0]
    assert "TOTAL_EXPANSIONISM" in prompt_1
    
    # 2. Propose with DIFFERENT strategy
    minister.propose(strategy=GlobalStrategy.COALITION_BUILDER, turn=2)
    prompt_2 = mock_client.query_agent.call_args[0][0]
    
    assert prompt_1 == prompt_2
    assert "TOTAL_EXPANSIONISM" in prompt_2
    # Removed incorrect exclusion check for 'COALITION_BUILDER' as it appears in boilerplate examples.

def test_economy_minister_prompt_remains_static(setup_agent, mock_client):
    """Verify Economy Minister prompt remains static."""
    agent, _ = setup_agent
    minister = agent.economy_minister
    
    minister.propose(strategy=GlobalStrategy.TOTAL_EXPANSIONISM, turn=1)
    prompt_1 = mock_client.query_agent.call_args[0][0]
    
    minister.propose(strategy=GlobalStrategy.ARMED_ISOLATIONISM, turn=2)
    prompt_2 = mock_client.query_agent.call_args[0][0]
    
    assert prompt_1 == prompt_2

def test_caching_perfection(setup_agent, mock_client):
    """Verify that the prompt object reference remains the same (no redundant regeneration)."""
    agent, world = setup_agent
    
    mock_briefing = MagicMock()
    mock_briefing.defense = MagicMock(spec=DefenseProposal); mock_briefing.defense.payload = MagicMock(); mock_briefing.defense.payload.moves = []
    mock_briefing.defense.intent = MagicMock(); mock_briefing.defense.intent.public_intent.value = "DETERRENCE"
    mock_briefing.defense.intent.private_intent.value = "DETERRENCE"; mock_briefing.defense.intent.reasoning = "Test"
    mock_briefing.economy.payload = MagicMock(); mock_briefing.economy.payload.amount = 100.0; mock_briefing.economy.payload.give_type = None; mock_briefing.economy.payload.want_type = None
    mock_briefing.economy.intent = MagicMock(); mock_briefing.economy.intent.public_intent.value = "GROWTH"; mock_briefing.economy.intent.private_intent.value = "GROWTH"; mock_briefing.economy.intent.reasoning = "Test"
    mock_briefing.foreign.payload = MagicMock(); mock_briefing.foreign.payload.target_nation_id = "B"; mock_briefing.foreign.payload.diplomatic_message_type = None; mock_briefing.foreign.payload.proposal_ref_type = None
    mock_briefing.foreign.intent = MagicMock(); mock_briefing.foreign.intent.public_intent.value = "COOPERATION"; mock_briefing.foreign.intent.private_intent.value = "COOPERATION"; mock_briefing.foreign.intent.reasoning = "Test"

    agent._presidential_decision(turn=1, briefing=mock_briefing)
    cached_prompt = agent.president_system_prompt
    
    # Change strategy and call again
    agent.strategy = GlobalStrategy.ARMED_ISOLATIONISM
    agent._presidential_decision(turn=2, briefing=mock_briefing)
    
    assert agent.president_system_prompt is cached_prompt
