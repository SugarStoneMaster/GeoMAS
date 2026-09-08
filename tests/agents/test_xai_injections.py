import pytest
from unittest.mock import MagicMock, patch
from geomas.agents.nation_agent import NationAgent
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType
from geomas.agents.llm_client import LLMClient
from geomas.agents.schemas import (
    PresidentialDecree, DefenseProposal, EconomicProposal, ForeignProposal,
    DefenseIntent, DefenseIntentType, EconomicIntent,
    ForeignIntent, ForeignIntentType, GlobalStrategy, PresidentialDecision,
    DefenseDecree, EconomicDecree, ForeignDecree, CountryEnvelope, CabinetBriefing
)
from geomas.actions.defense.schemas import DefenseProposalPayload, DefensePayload
from geomas.actions.economy.schemas import EconomicProposalPayload, EconomicActionType, EconomicPayload
from geomas.actions.foreign.schemas import ForeignProposalPayload, ForeignActionType, ForeignPayload

@pytest.fixture
def clean_world():
    world = WorldState(turn=1)
    # Add dummy provinces to avoid KeyError
    world.provinces = {
        1: ProvinceState(id=1, owner_id="VALKYR", terrain=TerrainType.LAND, coordinates=(0,0)),
        2: ProvinceState(id=2, owner_id="VALKYR", terrain=TerrainType.LAND, coordinates=(1,1)),
        3: ProvinceState(id=3, owner_id="ENEMY", terrain=TerrainType.LAND, coordinates=(2,2)),
        4: ProvinceState(id=4, owner_id="ENEMY", terrain=TerrainType.LAND, coordinates=(3,3))
    }
    valkyr = NationState(
        id="VALKYR",
        name="VALKYR",
        color="#FF0000",
        total_budget=1000,
        province_ids=[1, 2],
        total_soldiers=1000,
        total_aircraft=50,
        total_navy=10
    )
    enemy = NationState(
        id="ENEMY",
        name="ENEMY",
        color="#0000FF",
        province_ids=[3, 4]
    )
    world.nations = {"VALKYR": valkyr, "ENEMY": enemy}
    world.relationship_matrix = {"VALKYR": {"ENEMY": "PEACE"}, "ENEMY": {"VALKYR": "PEACE"}}
    world.trust_matrix = {"VALKYR": {"ENEMY": 50}, "ENEMY": {"VALKYR": 50}}
    return world

def test_nation_agent_collects_injections_for_president(clean_world):
    client = MagicMock(spec=LLMClient)
    client.last_raw_content = '{"raw": "json"}'
    
    # Mock minister proposals
    def_prop = DefenseProposal(
        intent=DefenseIntent(public_intent=DefenseIntentType.IDLE, private_intent=DefenseIntentType.IDLE, reasoning="R"),
        payload=DefenseProposalPayload(moves=[])
    )
    eco_prop = EconomicProposal(
        intent=EconomicIntent(reasoning="R"),
        payload=EconomicProposalPayload(action_type=EconomicActionType.IDLE)
    )
    for_prop = ForeignProposal(
        intent=ForeignIntent(public_intent=ForeignIntentType.IDLE, private_intent=ForeignIntentType.IDLE, reasoning="R"),
        payload=ForeignProposalPayload(action_type=ForeignActionType.IDLE)
    )
    
    decree = PresidentialDecree(
        defense=DefenseDecree(action=PresidentialDecision.APPROVE, reasoning="OK"),
        economy=EconomicDecree(action=PresidentialDecision.APPROVE, reasoning="OK"),
        foreign=ForeignDecree(action=PresidentialDecision.APPROVE, reasoning="OK"),
        public_statement="Peace"
    )
    client.query_agent.return_value = decree
    
    agent = NationAgent("VALKYR", clean_world, client)
    
    briefing = CabinetBriefing(defense=def_prop, economy=eco_prop, foreign=for_prop)
    injections = ["DEFENSE: NOT perform action MOVE_TROOPS", "ECONOMY: perform action INVEST_WELFARE"]
    
    agent._presidential_decision(1, briefing, injections)
    
    # Get the user prompt passed to the President
    call_args = client.query_agent.call_args[0]
    user_prompt = call_args[1]
    
    assert "## ACTIVE STRATEGIC CONSTRAINTS (MANDATORY)" in user_prompt
    assert "DEFENSE: NOT PERFORM ACTION MOVE_TROOPS" in user_prompt
    assert "ECONOMY: PERFORM ACTION INVEST_WELFARE" in user_prompt

def test_envelope_captures_raw_president_response(clean_world):
    client = MagicMock(spec=LLMClient)
    client.last_raw_content = '{"president": "says yes"}'
    
    # Mock responses
    decree = PresidentialDecree(
        defense=DefenseDecree(action=PresidentialDecision.APPROVE, reasoning="OK"),
        economy=EconomicDecree(action=PresidentialDecision.APPROVE, reasoning="OK"),
        foreign=ForeignDecree(action=PresidentialDecision.APPROVE, reasoning="OK"),
        public_statement="Peace"
    )
    
    # Real payload objects to satisfy Pydantic
    def_prop = DefenseProposal(
        intent=DefenseIntent(public_intent=DefenseIntentType.IDLE, private_intent=DefenseIntentType.IDLE, reasoning="R"),
        payload=DefenseProposalPayload(moves=[])
    )
    eco_prop = EconomicProposal(
        intent=EconomicIntent(reasoning="R"),
        payload=EconomicProposalPayload(action_type=EconomicActionType.IDLE)
    )
    for_prop = ForeignProposal(
        intent=ForeignIntent(public_intent=ForeignIntentType.IDLE, private_intent=ForeignIntentType.IDLE, reasoning="R"),
        payload=ForeignProposalPayload(action_type=ForeignActionType.IDLE)
    )
    briefing = CabinetBriefing(defense=def_prop, economy=eco_prop, foreign=for_prop)

    agent = NationAgent("VALKYR", clean_world, client)
    
    # Manually set last_president_trace 
    agent.last_president_trace = {"raw_json": '{"president": "says yes"}'}
    
    # Simulate envelope construction
    envelope = agent._construct_envelope_from_decree(1, decree, briefing)
    
    assert envelope.raw_president_response == '{"president": "says yes"}'
