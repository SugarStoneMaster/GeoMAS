
import pytest
from geomas.agents.context.system.opinion import OpinionSystemPrompt

def test_opinion_prompt_multipliers():
    """Verify that the Opinion prompt mentions the correct multipliers and not delta."""
    prompt = OpinionSystemPrompt.generate("TestNation")
    
    # Check for correct multipliers
    assert "multiplier_increase" in prompt
    assert "multiplier_decrease" in prompt
    
    # Ensure satisfaction_delta is NOT requested (old behavior)
    assert "satisfaction_delta" not in prompt
    
    # Check for range instructions
    assert "0.1 to 2.0" in prompt

def test_opinion_prompt_mechanics():
    """Verify that the Opinion prompt mentions Strike and Unrest mechanics."""
    prompt = OpinionSystemPrompt.generate("TestNation")
    
    assert "General Strike" in prompt
    assert "Civil Unrest" in prompt
    assert "20" in prompt  # Strike threshold
    assert "10" in prompt  # Unrest threshold

def test_opinion_prompt_structure():
    """Verify that the Opinion prompt follows the ministerial structure."""
    prompt = OpinionSystemPrompt.generate("TestNation")
    
    assert "Your Responsibilities" in prompt
    assert "Mechanics & Consequences" in prompt
    assert "Guidelines" in prompt
    assert "Output Requirements" in prompt
    assert "Research Framework" not in prompt
    assert "Evaluation Lenses" not in prompt

def test_opinion_prompt_analytical_content():
    """Verify that the Opinion prompt contains the naturalized analytical responsibilities."""
    prompt = OpinionSystemPrompt.generate("TestNation")
    
    assert "Geographic Evaluation" in prompt
    assert "Narrative Assessment" in prompt
    assert "Stability Monitoring" in prompt
    assert "moral washing" in prompt.lower()
    
def test_opinion_prompt_cultural_traits():
    """Verify cultural traits are correctly injected."""
    traits = ["Militarist", "Rich history", "Agricultural"]
    prompt = OpinionSystemPrompt.generate("TestNation", cultural_traits=traits)
    
    for trait in traits:
        assert trait in prompt
