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
    from geomas.agents.schemas import (
        PresidentialDecree, PresidentialDecision, DefenseDecree, EconomicDecree, ForeignDecree, EconomicIntent
    )

    dummy_defense = DefenseProposal(
        intent=DefenseIntent(public_intent=DefenseIntentType.IDLE, private_intent=DefenseIntentType.IDLE, reasoning="T"), 
        payload=DefensePayload(moves=[])
    )
    dummy_economy = EconomicProposal(
        intent=EconomicIntent(reasoning="T"),
        payload=EconomicPayload(action_type=EconomicActionType.IDLE)
    )
    dummy_foreign = ForeignProposal(
        intent=ForeignIntent(public_intent=ForeignIntentType.IDLE, private_intent=ForeignIntentType.IDLE, reasoning="T"),
        payload=ForeignPayload(action_type=ForeignActionType.IDLE)
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


def mock_engine_llm(engine):
    """Helper to mock LLM calls for an engine instance."""
    from geomas.agents.schemas import DefenseProposal, DefenseIntent, DefenseIntentType
    from geomas.actions.defense.schemas import DefensePayload
    from geomas.agents.schemas import EconomicProposal
    from geomas.actions.economy.schemas import EconomicPayload, EconomicActionType
    from geomas.agents.schemas import ForeignProposal, ForeignIntent, ForeignIntentType
    from geomas.actions.foreign.schemas import ForeignPayload, ForeignActionType
    from geomas.agents.schemas import (
        PresidentialDecree, PresidentialDecision, DefenseDecree, EconomicDecree, ForeignDecree, EconomicIntent
    )

    dummy_defense = DefenseProposal(
        intent=DefenseIntent(public_intent=DefenseIntentType.IDLE, private_intent=DefenseIntentType.IDLE, reasoning="T"), 
        payload=DefensePayload(moves=[])
    )
    dummy_economy = EconomicProposal(
        intent=EconomicIntent(reasoning="T"),
        payload=EconomicPayload(action_type=EconomicActionType.IDLE)
    )
    dummy_foreign = ForeignProposal(
        intent=ForeignIntent(public_intent=ForeignIntentType.IDLE, private_intent=ForeignIntentType.IDLE, reasoning="T"),
        payload=ForeignPayload(action_type=ForeignActionType.IDLE)
    )
    dummy_president = PresidentialDecree(
        defense=DefenseDecree(action=PresidentialDecision.APPROVE, reasoning="T"),
        economy=EconomicDecree(action=PresidentialDecision.APPROVE, reasoning="T"),
        foreign=ForeignDecree(action=PresidentialDecision.APPROVE, reasoning="T"),
        public_statement="T"
    )

    engine.client.aquery_agent = AsyncMock()
    engine.client.aquery_agent.return_value = dummy_defense # Simplification, return dummy_defense for all since structure isn't strictly checked by default engine step unless it expects specific type. Wait, side_effect is better to match expected sequence.
    # Actually, the engine expects Defense, Economy, Foreign in sequence for each nation.
    # Let's use a side effect that just repeats. We can use a custom mock that returns the right type based on the response_model.
    
    async def mock_aquery(*args, **kwargs):
        rm = kwargs.get('response_model')
        if rm == DefenseProposal: return dummy_defense
        if rm == EconomicProposal: return dummy_economy
        if rm == ForeignProposal: return dummy_foreign
        return dummy_defense # fallback

    engine.client.aquery_agent.side_effect = mock_aquery
    engine.client.query_agent = MagicMock(return_value=dummy_president)

    for nation_id, o_agent in engine.opinion_agents.items():
        from geomas.agents.opinion import OpinionResponse
        class MockResponse:
            multiplier_increase = 1.0
            multiplier_decrease = 1.0
            mood = "NEUTRAL"
            reasoning = "Test"
            raw_json = "{}"
        o_agent.react = MagicMock(return_value=MockResponse())


def test_resource_discovery_scenario_trigger():
    engine = SimulationEngine(n_nations=4, map_seed=12)
    mock_engine_llm(engine)
    world = engine.world
    
    # Store pre-discovery energy sum
    pre_energy_sum = sum(p.energy_production for p in world.provinces.values() if p.owner_id)
    
    scenario_trigger = {"type": "RESOURCE_DISCOVERY", "turn": 2}
    
    # Run turn 1
    engine.step(scenario_trigger=scenario_trigger)
    post_turn1_energy_sum = sum(p.energy_production for p in world.provinces.values() if p.owner_id)
    assert abs(post_turn1_energy_sum - pre_energy_sum) < 0.1 # unchanged
    
    # Run turn 2 (Resource discovery triggers)
    engine.step(scenario_trigger=scenario_trigger)
    post_turn2_energy_sum = sum(p.energy_production for p in world.provinces.values() if p.owner_id)
    assert post_turn2_energy_sum > pre_energy_sum + 10 # Clearly increased significantly

    has_event = any(e.event_type.value == "GLOBAL_SCENARIO" for e in engine.context_manager.global_events)
    assert has_event


def test_separatist_insurrection_scenario_trigger():
    engine = SimulationEngine(n_nations=4, map_seed=20)
    mock_engine_llm(engine)
    world = engine.world
    
    # Make sure one nation has very low satisfaction
    target_nation = list(world.nations.values())[0]
    target_nation.public_satisfaction = 10.0
    
    pre_nations_count = len(world.nations)
    
    scenario_trigger = {"type": "SEPARATIST_INSURRECTION", "turn": 1}
    engine.step(scenario_trigger=scenario_trigger)
    
    # Assert a new nation was created
    post_nations_count = len(world.nations)
    assert post_nations_count == pre_nations_count + 1
    
    # Find the rebel nation
    rebel_nation = [n for n in world.nations.values() if n.id.endswith("_FREE")]
    assert len(rebel_nation) == 1
    rebel = rebel_nation[0]
    
    # Check that they are at war with the motherland
    assert world.relationship_matrix[rebel.id][target_nation.id].value == "WAR"
    

def test_regime_change_scenario_trigger():
    engine = SimulationEngine(n_nations=4, map_seed=12)
    mock_engine_llm(engine)
    world = engine.world
    
    target_nation_id = list(world.nations.keys())[0]
    target_nation = world.nations[target_nation_id]
    
    # Before change
    original_gov = target_nation.government_type
    original_strat = target_nation.global_strategy
    
    # Pick different ones
    new_gov = "THEOCRACY" if original_gov != "THEOCRACY" else "DEMOCRACY"
    new_strat = "TOTAL_EXPANSIONISM" if original_strat != "TOTAL_EXPANSIONISM" else "COALITION_BUILDER"
    
    # Test case insensitivity on target_id
    scenario_trigger = {
        "type": "REGIME_CHANGE", 
        "turn": 1, 
        "target_id": target_nation_id.lower(), # lower case targeted
        "new_gov": new_gov,
        "new_strategy": new_strat
    }
    
    engine.step(scenario_trigger=scenario_trigger)
    
    # Should have updated the nation
    assert target_nation.government_type == new_gov
    assert target_nation.global_strategy == new_strat
    
    # Check private event
    has_event = any(e.event_type.value == "REGIME_CHANGE" and target_nation_id in e.relevance_to for e in engine.context_manager.global_events)
    assert has_event
