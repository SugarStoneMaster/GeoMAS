
import pytest
from unittest.mock import MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas import GlobalStrategy

class TestStrategyDistribution:
    """Verifies deterministic strategy and governance assignment logic."""

    def test_distribution_n4(self):
        """N=4: Should match the hardcoded exact profile."""
        engine = SimulationEngine(n_nations=4, map_seed=42)
        profiles = [(agent.strategy, agent.government_type) for agent in engine.agents.values()]
        
        assert len(profiles) == 4
        assert profiles.count((GlobalStrategy.TOTAL_EXPANSIONISM, "AUTHORITARIAN")) == 1
        assert profiles.count((GlobalStrategy.COALITION_BUILDER, "DEMOCRACY")) == 1
        assert profiles.count((GlobalStrategy.ARMED_ISOLATIONISM, "THEOCRACY")) == 1
        assert profiles.count((GlobalStrategy.SCORCHED_EARTH, "AUTHORITARIAN")) == 1

    def test_distribution_n6(self):
        """N=6: Should match the hardcoded exact profile."""
        engine = SimulationEngine(n_nations=6, map_seed=42)
        profiles = [(agent.strategy, agent.government_type) for agent in engine.agents.values()]
        
        assert len(profiles) == 6
        assert profiles.count((GlobalStrategy.TOTAL_EXPANSIONISM, "AUTHORITARIAN")) == 1
        assert profiles.count((GlobalStrategy.TOTAL_EXPANSIONISM, "DEMOCRACY")) == 1
        assert profiles.count((GlobalStrategy.COALITION_BUILDER, "DEMOCRACY")) == 2
        assert profiles.count((GlobalStrategy.ARMED_ISOLATIONISM, "THEOCRACY")) == 1
        assert profiles.count((GlobalStrategy.SCORCHED_EARTH, "AUTHORITARIAN")) == 1

    def test_distribution_n8(self):
        """N=8: Should match the hardcoded exact profile."""
        engine = SimulationEngine(n_nations=8, map_seed=42)
        profiles = [(agent.strategy, agent.government_type) for agent in engine.agents.values()]
        
        assert len(profiles) == 8
        assert profiles.count((GlobalStrategy.TOTAL_EXPANSIONISM, "AUTHORITARIAN")) == 1
        assert profiles.count((GlobalStrategy.TOTAL_EXPANSIONISM, "DEMOCRACY")) == 1
        assert profiles.count((GlobalStrategy.COALITION_BUILDER, "DEMOCRACY")) == 3
        assert profiles.count((GlobalStrategy.ARMED_ISOLATIONISM, "DEMOCRACY")) == 1
        assert profiles.count((GlobalStrategy.ARMED_ISOLATIONISM, "THEOCRACY")) == 1
        assert profiles.count((GlobalStrategy.SCORCHED_EARTH, "AUTHORITARIAN")) == 1

    def test_distribution_fallback(self):
        """N=5: Should use the fallback logic (base 4 + 1 fill)."""
        engine = SimulationEngine(n_nations=5, map_seed=42)
        strategies = [agent.strategy for agent in engine.agents.values()]
        
        assert len(strategies) == 5
        # Fallback ensures base 4
        assert GlobalStrategy.TOTAL_EXPANSIONISM in strategies
        assert GlobalStrategy.COALITION_BUILDER in strategies
        assert GlobalStrategy.ARMED_ISOLATIONISM in strategies
        assert GlobalStrategy.SCORCHED_EARTH in strategies

    def test_determinism(self):
        """Same seed yields same distribution (who gets what)."""
        engine1 = SimulationEngine(n_nations=6, map_seed=123)
        mapping1 = {id: (agent.strategy, agent.government_type) for id, agent in engine1.agents.items()}
        
        engine2 = SimulationEngine(n_nations=6, map_seed=123)
        mapping2 = {id: (agent.strategy, agent.government_type) for id, agent in engine2.agents.items()}
        
        assert mapping1 == mapping2
        
    def test_randomness(self):
        """Different seeds yield different assignments."""
        engine1 = SimulationEngine(n_nations=6, map_seed=123)
        mapping1 = {id: (agent.strategy, agent.government_type) for id, agent in engine1.agents.items()}
        
        engine2 = SimulationEngine(n_nations=6, map_seed=456)
        mapping2 = {id: (agent.strategy, agent.government_type) for id, agent in engine2.agents.items()}
        
        assert mapping1 != mapping2
