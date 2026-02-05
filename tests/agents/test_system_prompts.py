"""
Tests for System Prompts.
"""

import pytest
from geomas.agents.context.system import (
    PresidentSystemPrompt,
    DefenseSystemPrompt,
    EconomySystemPrompt,
    ForeignSystemPrompt,
    OpinionSystemPrompt,
)
from geomas.agents.schemas import GlobalStrategy


class TestPresidentSystemPrompt:
    """Tests for President system prompt."""
    
    def test_generates_prompt(self):
        """Can generate a president system prompt."""
        prompt = PresidentSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER
        )
        assert "President" in prompt
        assert "Testland" in prompt
        assert "Coalition Builder" in prompt
    
    def test_all_strategies_have_descriptions(self):
        """All GlobalStrategy values produce valid prompts."""
        for strategy in GlobalStrategy:
            prompt = PresidentSystemPrompt.generate("Test", strategy)
            assert len(prompt) > 500  # Reasonable length
    
    def test_includes_cultural_traits(self):
        """Cultural traits appear in prompt when provided."""
        prompt = PresidentSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.ARMED_ISOLATIONISM,
            cultural_traits=["proud", "warrior"]
        )
        assert "proud" in prompt
        assert "warrior" in prompt


class TestDefenseSystemPrompt:
    """Tests for Defense Minister system prompt."""
    
    def test_generates_prompt(self):
        """Can generate a defense system prompt."""
        prompt = DefenseSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.TOTAL_EXPANSIONISM
        )
        assert "Defense Minister" in prompt
        assert "Testland" in prompt
    
    def test_includes_military_actions(self):
        """Prompt includes available military actions."""
        prompt = DefenseSystemPrompt.generate("Test", GlobalStrategy.ARMED_ISOLATIONISM)
        assert "MOVE_TROOPS" in prompt or "ATTACK" in prompt


class TestEconomySystemPrompt:
    """Tests for Economy Minister system prompt."""
    
    def test_generates_prompt(self):
        """Can generate an economy system prompt."""
        prompt = EconomySystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.MERCANTILE_HEGEMONY
        )
        assert "Economy Minister" in prompt
        assert "Testland" in prompt
    
    def test_includes_satisfaction_info(self):
        """Prompt mentions satisfaction management."""
        prompt = EconomySystemPrompt.generate("Test", GlobalStrategy.DOMESTIC_RECOVERY)
        assert "satisfaction" in prompt.lower()
        assert "INVEST_IN_WELFARE" in prompt or "welfare" in prompt.lower()


class TestForeignSystemPrompt:
    """Tests for Foreign Minister system prompt."""
    
    def test_generates_prompt(self):
        """Can generate a foreign system prompt."""
        prompt = ForeignSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER
        )
        assert "Foreign Minister" in prompt
        assert "Testland" in prompt
    
    def test_includes_trust_mechanics(self):
        """Prompt explains trust mechanics."""
        prompt = ForeignSystemPrompt.generate("Test", GlobalStrategy.COALITION_BUILDER)
        assert "trust" in prompt.lower() or "Trust" in prompt


class TestOpinionSystemPrompt:
    """Tests for Public Opinion system prompt."""
    
    def test_generates_prompt(self):
        """Can generate an opinion system prompt."""
        prompt = OpinionSystemPrompt.generate(nation_name="Testland")
        assert "people" in prompt.lower()
        assert "Testland" in prompt
    
    def test_includes_cultural_traits(self):
        """Cultural traits appear when provided."""
        prompt = OpinionSystemPrompt.generate(
            nation_name="Testland",
            cultural_traits=["peaceful", "merchants"]
        )
        assert "peaceful" in prompt
        assert "merchants" in prompt
    
    def test_includes_satisfaction_scale(self):
        """Prompt explains satisfaction scale."""
        prompt = OpinionSystemPrompt.generate("Test")
        assert "satisfaction" in prompt.lower() or "Satisfaction" in prompt
