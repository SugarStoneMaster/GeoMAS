import pytest
from unittest.mock import patch, MagicMock
from geomas.agents.llm_client import LLMClient
from pydantic import BaseModel

class DummyResponse(BaseModel):
    test_field: str

@pytest.fixture
def mock_litellm():
    with patch('geomas.agents.llm_client.completion') as mock_comp, \
         patch('geomas.agents.llm_client.acompletion') as mock_acomp, \
         patch('geomas.agents.llm_client.instructor') as mock_inst:
        
        # Setup mock instructor client
        mock_client = MagicMock()
        mock_inst.from_litellm.return_value = mock_client
        
        # Setup mock response from instructor
        mock_response = DummyResponse(test_field="success")
        mock_client.chat.completions.create_with_completion.return_value = (mock_response, MagicMock())
        mock_client.chat.completions.create.return_value = mock_response
        
        yield mock_client

def test_deterministic_seed_generation(mock_litellm):
    """Test that map_seed combined with context generates a consistent seed parameter."""
    client = LLMClient(model_name="test-model", map_seed=42)
    
    system_prompt = "You are the **Defense Minister of NORD**"
    user_prompt = "## TURN 10\nReport status."
    
    client.query_agent(system_prompt, user_prompt, DummyResponse)
    
    # Verify the seed was injected into the litellm call via kwargs
    mock_litellm.chat.completions.create_with_completion.assert_called_once()
    _, kwargs = mock_litellm.chat.completions.create_with_completion.call_args
    
    assert "seed" in kwargs, "Seed parameter was not passed to API"
    assert isinstance(kwargs["seed"], int), "Seed must be an integer"
    
    # Now let's test isolation: Same turn, different role
    mock_litellm.reset_mock()
    system_prompt_2 = "You are the **Foreign Minister of NORD**"
    client.query_agent(system_prompt_2, user_prompt, DummyResponse)
    
    _, kwargs_2 = mock_litellm.chat.completions.create_with_completion.call_args
    assert kwargs_2["seed"] != kwargs["seed"], "Different roles should have different seeds!"
    
    # Now let's test consistency: Same inputs should yield same seed
    mock_litellm.reset_mock()
    client.query_agent(system_prompt, user_prompt, DummyResponse)
    _, kwargs_3 = mock_litellm.chat.completions.create_with_completion.call_args
    assert kwargs_3["seed"] == kwargs["seed"], "Identical contexts must produce identical seeds!"

def test_no_map_seed_behavior(mock_litellm):
    """Test that if map_seed is not provided, no seed is injected."""
    client = LLMClient(model_name="test-model", map_seed=None)
    
    system_prompt = "You are the **Defense Minister of NORD**"
    user_prompt = "## TURN 10\nReport status."
    
    client.query_agent(system_prompt, user_prompt, DummyResponse)
    
    mock_litellm.chat.completions.create_with_completion.assert_called_once()
    _, kwargs = mock_litellm.chat.completions.create_with_completion.call_args
    
    assert "seed" not in kwargs, "Seed parameter should not be present if map_seed is None"
