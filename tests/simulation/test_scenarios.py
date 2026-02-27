"""
Tests for Mid-Simulation Scenarios (e.g. Pandemic).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.simulation.scenarios import trigger_pandemic

def test_pandemic_scenario_trigger():
    """Test that the pandemic scenario correctly alters yields and population."""
    engine = SimulationEngine(n_nations=4, map_seed=12)
    
    # Mock LLM calls to avoid hanging tests
    from geomas.agents.schemas import DefenseProposal, DefenseIntent, DefenseIntentType
    from geomas.actions.defense.schemas import DefensePayload
    from geomas.agents.schemas import EconomicProposal
    from geomas.actions.economy.schemas import EconomicPayload, EconomicActionType
    from geomas.agents.schemas import ForeignProposal, ForeignIntent, ForeignIntentType
    from geomas.actions.foreign.schemas import ForeignPayload, ForeignActionType
    from geomas.agents.schemas import PresidentialDecree, PresidentialDecision, DefenseDecree, EconomicDecree, ForeignDecree

    dummy_defense = DefenseProposal(
        intent=DefenseIntent(public_intent=DefenseIntentType.IDLE, private_intent=DefenseIntentType.IDLE, reasoning="T"), 
        payload=DefensePayload(moves=[])
    )
    dummy_economy = EconomicProposal(
        payload=EconomicPayload(action_type=EconomicActionType.IDLE), projected_cost=0
    )
    dummy_foreign = ForeignProposal(
        intent=ForeignIntent(public_intent=ForeignIntentType.IDLE, private_intent=ForeignIntentType.IDLE, reasoning="T"),
        payload=ForeignPayload(action_type=ForeignActionType.IDLE), target_trust_impact=0
    )
    dummy_president = PresidentialDecree(
        defense=DefenseDecree(action=PresidentialDecision.APPROVE, reasoning="T"),
        economy=EconomicDecree(action=PresidentialDecision.APPROVE, reasoning="T"),
        foreign=ForeignDecree(action=PresidentialDecision.APPROVE, reasoning="T"),
        public_statement="T"
    )

    engine.client.aquery_agent = AsyncMock()
    engine.client.aquery_agent.side_effect = [
        dummy_defense, dummy_economy, dummy_foreign,
        dummy_defense, dummy_economy, dummy_foreign,
        dummy_defense, dummy_economy, dummy_foreign,
        dummy_defense, dummy_economy, dummy_foreign,
        dummy_defense, dummy_economy, dummy_foreign,
        dummy_defense, dummy_economy, dummy_foreign,
        dummy_defense, dummy_economy, dummy_foreign,
        dummy_defense, dummy_economy, dummy_foreign,
    ]
    engine.client.query_agent = MagicMock(return_value=dummy_president)
    
    # Also mock OpinionAgent to prevent pydantic error that happened earlier in test_injection.py
    for nation_id, o_agent in engine.opinion_agents.items():
        from geomas.agents.opinion import OpinionResponse
        import uuid
        class MockResponse:
            multiplier_increase = 1.0
            multiplier_decrease = 1.0
            mood = "NEUTRAL"
            reasoning = "Test"
            raw_json = "{}"
        o_agent.react = MagicMock(return_value=MockResponse())

    world = engine.world
    
    # Store pre-pandemic state
    pre_food_yields = {}
    pre_populations = {}
    for prov_id, prov in world.provinces.items():
        if prov.population > 0:
            pre_food_yields[prov_id] = prov.food_production
            pre_populations[prov_id] = prov.population
            
    nation_id = list(world.nations.keys())[0]
    pre_satisfaction = world.nations[nation_id].public_satisfaction
    
    # Trigger scenario
    scenario_trigger = {"type": "PANDEMIA", "turn": 2}
    
    # Run turn 1 (Nothing happens)
    engine.step(scenario_trigger=scenario_trigger)
    
    # Assert nothing changed
    for prov_id, initial_yield in pre_food_yields.items():
        assert world.provinces[prov_id].food_production == initial_yield
        
    # Run turn 2 (Pandemic triggers)
    engine.step(scenario_trigger=scenario_trigger)
    
    # Assert pandemic effects: production halved (deterministic), population decreased (density-variable rate)
    for prov_id, initial_yield in pre_food_yields.items():
        assert world.provinces[prov_id].food_production == initial_yield * 0.5
        # Population must have decreased by at least 5% and at most 25% (density-based rate bounds)
        pre_pop = pre_populations[prov_id]
        post_pop = world.provinces[prov_id].population
        assert post_pop < pre_pop, f"Province {prov_id}: population did not decrease after pandemic"
        assert post_pop >= int(pre_pop * 0.75), f"Province {prov_id}: population loss exceeded 25% cap"

    # Satisfaction must have dropped by at least 10 points (even the most food-rich penalty is -15)
    assert world.nations[nation_id].public_satisfaction < pre_satisfaction - 10.0
    
    # Assert context manager event was injected
    has_event = any(e.event_type.value == "GLOBAL_SCENARIO" for e in engine.context_manager.global_events)
    assert has_event, "Global Scenario event not appended to ContextManager."
