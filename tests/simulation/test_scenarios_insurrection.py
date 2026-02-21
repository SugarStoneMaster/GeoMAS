"""
Tests for the Separatist Insurrection scenario.
"""

import pytest
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas import GlobalStrategy
from geomas.agents.schemas.protocol import GovernmentType
from geomas.schemas.world import RelationshipState

@pytest.fixture
def base_engine():
    """Creates a basic engine instance for testing."""
    from unittest.mock import MagicMock
    mock_client = MagicMock()
    
    engine = SimulationEngine(
        map_seed=42,
        history_seed=99,
        n_cells=100,
        n_nations=4,
        llm_client=mock_client
    )
    return engine

def test_separatist_insurrection_triggers_correctly(base_engine):
    """
    Test that the scenario splits the nation, transfers properties,
    and returns correct instantiation data.
    """
    world = base_engine.world
    cm = base_engine.context_manager
    initial_nations_count = len(world.nations)
    
    # 1. Force a nation to have lowest satisfaction
    target_id = list(world.nations.keys())[0]
    target_nation = world.nations[target_id]
    target_nation.public_satisfaction = 10.0 # Lowest
    
    for n_id, n in world.nations.items():
        if n_id != target_id:
            n.public_satisfaction = 80.0
            
    # Count initial provinces and resources
    initial_provinces = len(target_nation.province_ids)
    assert initial_provinces > 1, "Target nation must have more than 1 province for rebellion."
    
    initial_budget = target_nation.total_budget
    
    # 2. Trigger Scenario
    scenario_trigger = {"type": "INSURREZIONE", "turn": 5}
    base_engine.world.turn = 5
    
    # Mock the immediate next function to halt execution before complex agent loops
    from unittest.mock import patch
    
    with patch('geomas.simulation.engine.run_upkeep_phase', side_effect=Exception("HaltForTest")):
        try:
            base_engine.step(scenario_trigger=scenario_trigger)
        except Exception as e:
            assert str(e) == "HaltForTest"
    
    # 3. Assertions
    # A new nation should be added
    assert len(world.nations) == initial_nations_count + 1
    
    rebel_id = f"{target_id}_FREE"
    assert rebel_id in world.nations
    rebel_nation = world.nations[rebel_id]
    
    # Motherland lost provinces, Rebel gained them
    final_provinces = len(target_nation.province_ids)
    rebel_provinces = len(rebel_nation.province_ids)
    assert final_provinces < initial_provinces
    assert rebel_provinces > 0
    assert final_provinces + rebel_provinces == initial_provinces
    
    # Check province ownership in WorldState
    for p_id in rebel_nation.province_ids:
        assert world.provinces[p_id].owner_id == rebel_id
        
    # Check resource splitting (rough approximation based on provinces taken)
    assert target_nation.total_budget < initial_budget
    assert rebel_nation.total_budget > 0
    
    # Check Agents were instantiated
    assert rebel_id in base_engine.agents
    assert rebel_id in base_engine.opinion_agents
    
    rebel_agent = base_engine.agents[rebel_id]
    
    # Check Government Type opposing motherland
    mother_gov_str = getattr(target_nation, "government_type", GovernmentType.DEMOCRACY.value)
    if mother_gov_str == GovernmentType.DEMOCRACY.value:
        assert rebel_agent.government_type == GovernmentType.AUTHORITARIAN
    elif mother_gov_str == GovernmentType.AUTHORITARIAN.value:
        assert rebel_agent.government_type == GovernmentType.DEMOCRACY
        
    # Check Trust/Relationship Matrix
    assert world.relationship_matrix[rebel_id][target_id] == RelationshipState.WAR
    assert world.relationship_matrix[target_id][rebel_id] == RelationshipState.WAR
    assert world.trust_matrix[rebel_id][target_id] == -100.0
    
    # Check Global Event logged
    events_t5 = [e for e in cm.global_events if e.turn == 5]
    assert len(events_t5) > 0
    assert any("CIVIL WAR" in e.summary or "Insurrection" in e.summary for e in events_t5)
