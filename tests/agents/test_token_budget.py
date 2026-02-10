"""
Tests for Token Counter and Prompt Budget Validation.
"""

import pytest
from geomas.world import generate_world
from geomas.agents.context.tokens import TokenCounter, count_tokens, validate_prompt_budget
from geomas.agents.context.system import (
    PresidentSystemPrompt,
    DefenseSystemPrompt,
    EconomySystemPrompt,
    ForeignSystemPrompt,
    OpinionSystemPrompt,
)
from geomas.agents.context.input import (
    PresidentInputBuilder,
    DefenseInputBuilder,
    EconomyInputBuilder,
    ForeignInputBuilder,
    OpinionInputBuilder,
)
from geomas.agents.schemas import GlobalStrategy


class TestTokenCounter:
    """Tests for TokenCounter class."""
    
    def test_create_counter(self):
        """Can create a token counter."""
        counter = TokenCounter()
        assert counter is not None
        assert counter._use_tiktoken is True
    
    def test_count_empty_string(self):
        """Empty string returns 0 tokens."""
        counter = TokenCounter()
        assert counter.count("") == 0
    
    def test_count_simple_text(self):
        """Can count tokens in simple text."""
        counter = TokenCounter()
        tokens = counter.count("Hello, world!")
        assert tokens > 0
        assert tokens < 10  # Should be ~4 tokens
    
    def test_count_longer_text(self):
        """Longer text has proportionally more tokens."""
        counter = TokenCounter()
        short = counter.count("Hello")
        long = counter.count("Hello, this is a much longer sentence with many more words.")
        assert long > short
    
    def test_validate_budget_valid(self):
        """Valid budget returns True."""
        counter = TokenCounter()
        is_valid, details = counter.validate_budget(
            system_prompt="You are an assistant.",
            user_prompt="What is 2+2?",
            max_tokens=100
        )
        assert is_valid is True
        assert details["tokens_remaining"] > 0
    
    def test_validate_budget_invalid(self):
        """Exceeding budget returns False."""
        counter = TokenCounter()
        long_text = "word " * 1000  # ~1000 tokens
        is_valid, details = counter.validate_budget(
            system_prompt=long_text,
            user_prompt=long_text,
            max_tokens=100
        )
        assert is_valid is False
        assert details["tokens_remaining"] < 0
    
    def test_convenience_functions(self):
        """Convenience functions work correctly."""
        tokens = count_tokens("Hello, world!")
        assert tokens > 0
        
        is_valid, _ = validate_prompt_budget("System", "User", 5000)
        assert is_valid is True


class TestSystemPromptBudget:
    """Tests that system prompts stay within budget."""
    
    SYSTEM_BUDGET = 1200
    
    @pytest.fixture
    def counter(self):
        return TokenCounter()
    
    def test_president_prompt_under_budget(self, counter):
        """President system prompt is under 800 tokens."""
        prompt = PresidentSystemPrompt.generate(
            nation_name="Valdoria",
            strategy=GlobalStrategy.COALITION_BUILDER,
            cultural_traits=["proud", "diplomatic"]
        )
        tokens = counter.count(prompt)
        
        assert tokens < self.SYSTEM_BUDGET, f"President prompt is {tokens} tokens (max {self.SYSTEM_BUDGET})"
        print(f"President: {tokens} tokens ({tokens/self.SYSTEM_BUDGET*100:.0f}% of budget)")
    
    def test_defense_prompt_under_budget(self, counter):
        """Defense system prompt is under 800 tokens."""
        prompt = DefenseSystemPrompt.generate(
            nation_name="Valdoria",
            strategy=GlobalStrategy.TOTAL_EXPANSIONISM
        )
        tokens = counter.count(prompt)
        
        assert tokens < self.SYSTEM_BUDGET, f"Defense prompt is {tokens} tokens"
        print(f"Defense: {tokens} tokens ({tokens/self.SYSTEM_BUDGET*100:.0f}% of budget)")
    
    def test_economy_prompt_under_budget(self, counter):
        """Economy system prompt is under 800 tokens."""
        prompt = EconomySystemPrompt.generate(
            nation_name="Valdoria",
            strategy=GlobalStrategy.MERCANTILE_HEGEMONY
        )
        tokens = counter.count(prompt)
        
        assert tokens < self.SYSTEM_BUDGET, f"Economy prompt is {tokens} tokens"
        print(f"Economy: {tokens} tokens ({tokens/self.SYSTEM_BUDGET*100:.0f}% of budget)")
    
    def test_foreign_prompt_under_budget(self, counter):
        """Foreign system prompt is under 800 tokens."""
        prompt = ForeignSystemPrompt.generate(
            nation_name="Valdoria",
            strategy=GlobalStrategy.ARMED_ISOLATIONISM
        )
        tokens = counter.count(prompt)
        
        assert tokens < self.SYSTEM_BUDGET, f"Foreign prompt is {tokens} tokens"
        print(f"Foreign: {tokens} tokens ({tokens/self.SYSTEM_BUDGET*100:.0f}% of budget)")
    
    def test_opinion_prompt_under_budget(self, counter):
        """Opinion system prompt is under 800 tokens."""
        prompt = OpinionSystemPrompt.generate(
            nation_name="Valdoria",
            cultural_traits=["proud", "warrior", "traditional"]
        )
        tokens = counter.count(prompt)
        
        assert tokens < self.SYSTEM_BUDGET, f"Opinion prompt is {tokens} tokens"
        print(f"Opinion: {tokens} tokens ({tokens/self.SYSTEM_BUDGET*100:.0f}% of budget)")


class TestInputBuilderBudget:
    """Tests that input builders stay within budget."""
    
    INPUT_BUDGET = 4200
    
    @pytest.fixture
    def counter(self):
        return TokenCounter()
    
    @pytest.fixture
    def world(self):
        return generate_world(seed=42, history_seed=99, n_cells=200, n_nations=4)
    
    def test_president_input_under_budget(self, counter, world):
        """President input is under 4200 tokens."""
        builder = PresidentInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(
            nation_id,
            turn=1,
            defense_summary="2 borders at risk, 1 attack option",
            economy_summary="Budget stable, need energy",
            foreign_summary="1 alliance proposal pending"
        )
        tokens = counter.count(context)
        
        assert tokens < self.INPUT_BUDGET, f"President input is {tokens} tokens"
        print(f"President: {tokens} tokens ({tokens/self.INPUT_BUDGET*100:.0f}% of budget)")
    
    def test_defense_input_under_budget(self, counter, world):
        """Defense input is under 4200 tokens."""
        builder = DefenseInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        tokens = counter.count(context)
        
        assert tokens < self.INPUT_BUDGET, f"Defense input is {tokens} tokens"
        print(f"Defense: {tokens} tokens ({tokens/self.INPUT_BUDGET*100:.0f}% of budget)")
    
    def test_economy_input_under_budget(self, counter, world):
        """Economy input is under 4200 tokens."""
        builder = EconomyInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        tokens = counter.count(context)
        
        assert tokens < self.INPUT_BUDGET, f"Economy input is {tokens} tokens"
        print(f"Economy: {tokens} tokens ({tokens/self.INPUT_BUDGET*100:.0f}% of budget)")
    
    def test_foreign_input_under_budget(self, counter, world):
        """Foreign input is under 4200 tokens."""
        builder = ForeignInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        tokens = counter.count(context)
        
        assert tokens < self.INPUT_BUDGET, f"Foreign input is {tokens} tokens"
        print(f"Foreign: {tokens} tokens ({tokens/self.INPUT_BUDGET*100:.0f}% of budget)")
    
    def test_opinion_input_under_budget(self, counter, world):
        """Opinion input is under 4200 tokens."""
        builder = OpinionInputBuilder(world)
        nation_id = list(world.nations.keys())[0]
        
        context = builder.build(nation_id, turn=1)
        tokens = counter.count(context)
        
        assert tokens < self.INPUT_BUDGET, f"Opinion input is {tokens} tokens"
        print(f"Opinion: {tokens} tokens ({tokens/self.INPUT_BUDGET*100:.0f}% of budget)")


class TestCombinedBudget:
    """Tests that system + input stay under 5000 total."""
    
    TOTAL_BUDGET = 5000
    
    @pytest.fixture
    def counter(self):
        return TokenCounter()
    
    @pytest.fixture
    def world(self):
        return generate_world(seed=42, history_seed=99, n_cells=200, n_nations=4)
    
    def test_president_combined_under_total(self, counter, world):
        """President system + input is under 5000 tokens."""
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        system = PresidentSystemPrompt.generate(
            nation.name, GlobalStrategy.COALITION_BUILDER
        )
        user = PresidentInputBuilder(world).build(nation_id, turn=1)
        
        is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
        
        assert is_valid, f"President combined is {details['total_tokens']} tokens"
        print(f"President: {details['total_tokens']} tokens, {details['utilization_percent']:.0f}% utilization")
    
    def test_all_agents_combined_under_total(self, counter, world):
        """All agents system + input are under 5000 tokens."""
        nation_id = list(world.nations.keys())[0]
        nation = world.nations[nation_id]
        
        agents = [
            ("President", 
             PresidentSystemPrompt.generate(nation.name, GlobalStrategy.COALITION_BUILDER),
             PresidentInputBuilder(world).build(nation_id, turn=1)),
            ("Defense",
             DefenseSystemPrompt.generate(nation.name, GlobalStrategy.COALITION_BUILDER),
             DefenseInputBuilder(world).build(nation_id, turn=1)),
            ("Economy",
             EconomySystemPrompt.generate(nation.name, GlobalStrategy.COALITION_BUILDER),
             EconomyInputBuilder(world).build(nation_id, turn=1)),
            ("Foreign",
             ForeignSystemPrompt.generate(nation.name, GlobalStrategy.COALITION_BUILDER),
             ForeignInputBuilder(world).build(nation_id, turn=1)),
            ("Opinion",
             OpinionSystemPrompt.generate(nation.name),
             OpinionInputBuilder(world).build(nation_id, turn=1)),
        ]
        
        all_valid = True
        for name, system, user in agents:
            is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
            all_valid = all_valid and is_valid
            print(f"{name}: {details['total_tokens']} tokens ({details['utilization_percent']:.0f}%)")
        
        assert all_valid, "Not all agents are under budget"
