import pytest
from unittest.mock import MagicMock, patch
from geomas.schemas.world import WorldState, NationState
from geomas.agents.nation_agent import NationAgent
from geomas.agents.schemas import GlobalStrategy
from geomas.agents.schemas.protocol import GovernmentType

@pytest.fixture
def mock_world():
    world = MagicMock(spec=WorldState)
    nation = MagicMock(spec=NationState)
    nation.name = "TestNation"
    nation.nukes = 0
    nation.strategy = GlobalStrategy.COALITION_BUILDER
    nation.government_type = GovernmentType.DEMOCRACY
    
    world.nations = {"TEST_NATION": nation}
    return world

def test_nuclear_injection_grants_nukes_and_clears_cache(mock_world):
    """
    Test that when an XAI injection forces NUCLEAR_OPTION,
    the agent grants 10 nukes to the nation and clears prompt caches.
    """
    mock_client = MagicMock()
    agent = NationAgent(
        nation_id="TEST_NATION",
        world=mock_world,
        llm_client=mock_client
    )
    
    # 1. Simulate state BEFORE injection
    # Force the prompts to be initialized so we can check if they get cleared
    agent.defense_minister.system_prompt = "OLD_DEFENSE_PROMPT"
    agent.foreign_minister.system_prompt = "OLD_FOREIGN_PROMPT"
    
    assert mock_world.nations["TEST_NATION"].nukes == 0
    
    # 2. Setup standard non-nuclear injection
    regular_injection = [
        {
            "nation_id": "TEST_NATION",
            "role": "DEFENSE",
            "action": "MOVE_TROOPS",
            "type": "FORCE"
        }
    ]
    
    # Mock out the async cabinet phase and presidential decree so act() completes
    with patch.object(agent, "_async_cabinet_phase") as mock_cabinet, \
         patch.object(agent, "_presidential_decision") as mock_pres, \
         patch.object(agent, "_construct_envelope_from_decree") as mock_env, \
         patch("geomas.agents.nation_agent.CabinetBriefing") as mock_briefing:
        
        # Configure mocks to return empty/dummy objects
        import asyncio
        async def dummy_cabinet(*args, **kwargs):
            return {}, {}, {}
        mock_cabinet.side_effect = dummy_cabinet
        mock_pres.return_value = MagicMock()
        mock_env.return_value = MagicMock()
        mock_briefing.return_value = MagicMock()
        
        # Run ACT with regular injection
        agent.act(turn=1, injections=regular_injection)
        
        # Nukes should STILL be 0, caches untouched
        assert mock_world.nations["TEST_NATION"].nukes == 0
        assert agent.defense_minister.system_prompt == "OLD_DEFENSE_PROMPT"
        assert agent.foreign_minister.system_prompt == "OLD_FOREIGN_PROMPT"
        
        # 3. Setup NUCLEAR injection
        nuclear_injection = [
            {
                "nation_id": "TEST_NATION",
                "role": "DEFENSE",
                "action": "NUCLEAR_OPTION",
                "type": "FORCE"
            }
        ]
        
        # Run ACT with NUCLEAR injection
        agent.act(turn=2, injections=nuclear_injection)
        
        # 4. ASSERTIONS
        # Nation must now have 10 nukes
        assert mock_world.nations["TEST_NATION"].nukes == 10
        # Prompts must be cleared so they are re-generated with nukes=10
        assert agent.defense_minister.system_prompt is None
        assert agent.foreign_minister.system_prompt is None

def test_nuclear_injection_forbidding_does_not_grant_nukes(mock_world):
    """
    Ensure we don't accidentally grant nukes if the injection FORBIDS nuclear strikes.
    """
    mock_client = MagicMock()
    agent = NationAgent(
        nation_id="TEST_NATION",
        world=mock_world,
        llm_client=mock_client
    )
    
    forbid_injection = [
        {
            "nation_id": "TEST_NATION",
            "role": "DEFENSE",
            "action": "NUCLEAR_OPTION",
            "type": "FORBID"
        }
    ]
    
    with patch.object(agent, "_async_cabinet_phase") as mock_cabinet, \
         patch.object(agent, "_presidential_decision") as mock_pres, \
         patch.object(agent, "_construct_envelope_from_decree") as mock_env, \
         patch("geomas.agents.nation_agent.CabinetBriefing") as mock_briefing:
        
        import asyncio
        async def dummy_cabinet(*args, **kwargs):
            return {}, {}, {}
        mock_cabinet.side_effect = dummy_cabinet
        mock_briefing.return_value = MagicMock()
        
        agent.act(turn=1, injections=forbid_injection)
        
        # Arsenal should remain 0
        assert mock_world.nations["TEST_NATION"].nukes == 0
