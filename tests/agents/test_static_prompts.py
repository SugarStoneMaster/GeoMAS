
import pytest
from unittest.mock import MagicMock, patch
from geomas.agents.ministers import DefenseMinister
from geomas.agents.schemas import GlobalStrategy

def test_defense_minister_prompt_is_static():
    """
    Verify that DefenseMinister only sets the prompt once and never updates it,
    even if propose is called with a different strategy.
    """
    # 1. Setup mocks
    mock_world = MagicMock()
    mock_world.nations = {"AGRIA": MagicMock()}
    mock_world.nations["AGRIA"].name = "Republic of Agria"
    mock_world.nations["AGRIA"].nukes = 0
    
    # Mock dependencies of propose() to avoid execution
    with patch("geomas.agents.ministers.DefenseInputBuilder") as MockIB, \
         patch("geomas.agents.ministers.get_dynamic_proposal_model") as MockDM:
        
        mock_client = MagicMock()
        minister = DefenseMinister("AGRIA", mock_world, mock_client, strategy=GlobalStrategy.COALITION_BUILDER)
        
        initial_prompt = minister.system_prompt
        assert initial_prompt is not None
        
        # 2. Call propose with DIFFERENT strategy
        # It should NOT trigger _update_prompt
        with patch.object(DefenseMinister, "_update_prompt", wraps=minister._update_prompt) as mock_update:
            minister._update_prompt = mock_update
            
            minister.propose(GlobalStrategy.TOTAL_EXPANSIONISM, turn=2)
            
            assert minister.system_prompt == initial_prompt
            mock_update.assert_not_called()

def test_defense_minister_lazy_init():
    """Verify lazy init happens exactly once if strategy was None at __init__."""
    mock_world = MagicMock()
    mock_world.nations = {"AGRIA": MagicMock()}
    mock_world.nations["AGRIA"].name = "Republic of Agria"
    mock_world.nations["AGRIA"].nukes = 0
    
    with patch("geomas.agents.ministers.DefenseInputBuilder"), \
         patch("geomas.agents.ministers.get_dynamic_proposal_model"):
        
        mock_client = MagicMock()
        minister = DefenseMinister("AGRIA", mock_world, mock_client, strategy=None)
        
        assert minister.system_prompt is None
        
        # First call -> Inits
        minister.propose(GlobalStrategy.COALITION_BUILDER, turn=1)
        assert minister.system_prompt is not None
        cached_prompt = minister.system_prompt
        
        # Second call with different strategy -> Should NOT update
        with patch.object(DefenseMinister, "_update_prompt") as mock_update:
            minister.propose(GlobalStrategy.TOTAL_EXPANSIONISM, turn=2)
            assert minister.system_prompt == cached_prompt
            mock_update.assert_not_called()

if __name__ == "__main__":
    pytest.main([__file__])
