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
    
    # Motherland lost 25% of provinces, Rebel gained them
    final_provinces = len(target_nation.province_ids)
    rebel_provinces = len(rebel_nation.province_ids)
    expected_stolen = max(1, int(initial_provinces * 0.25))
    
    assert rebel_provinces == expected_stolen
    assert final_provinces == initial_provinces - expected_stolen
    
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
        
    # Check Trust/Relationship Matrix (Normalized 0-100)
    # Motherland relationship
    assert world.relationship_matrix[rebel_id][target_id] == RelationshipState.WAR
    assert world.relationship_matrix[target_id][rebel_id] == RelationshipState.WAR
    assert world.trust_matrix[rebel_id][target_id] == 0.0
    
    # Other nations relationship
    for other_id in world.nations:
        if other_id not in [rebel_id, target_id]:
            assert world.trust_matrix[rebel_id][other_id] >= 0.0
            assert world.trust_matrix[rebel_id][other_id] <= 100.0
    
    # Check Global Event logged
    events_t5 = [e for e in cm.global_events if e.turn == 5]
    assert len(events_t5) > 0
    assert any("CIVIL WAR" in e.summary or "Insurrection" in e.summary for e in events_t5)

def test_trust_matrix_diagonal_initialization(base_engine):
    """
    Verifies that a new rebel nation has its self-trust (diagonal) 
    initialized correctly to 100 in the trust matrix.
    """
    world = base_engine.world
    target_id = list(world.nations.keys())[0]
    world.nations[target_id].public_satisfaction = 0.0
    
    # Trigger Scenario
    # We call the trigger directly to avoid full engine complexity in this unit test
    from geomas.simulation.scenarios import trigger_separatist_insurrection
    trigger_separatist_insurrection(world, base_engine.context_manager, 10)
    
    rebel_id = f"{target_id}_FREE"
    assert rebel_id in world.trust_matrix
    assert rebel_id in world.trust_matrix[rebel_id]
    assert world.trust_matrix[rebel_id][rebel_id] == 100.0
    
    assert rebel_id in world.relationship_matrix
    assert rebel_id in world.relationship_matrix[rebel_id]
    # Check that it's initialized (e.g., to "SELF" or "PEACE")
    assert world.relationship_matrix[rebel_id][rebel_id] == "SELF"
