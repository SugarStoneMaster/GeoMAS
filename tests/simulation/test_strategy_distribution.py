
import pytest
from unittest.mock import MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas import GlobalStrategy

class TestStrategyDistribution:
    """Verifies deterministic strategy assignment logic."""

    def test_distribution_small_n(self):
        """N=2: Should pick top 2 priorities (EXP + COAL)."""
        engine = SimulationEngine(n_nations=2, map_seed=42)
        strategies = [agent.strategy for agent in engine.agents.values()]
        
        assert len(strategies) == 2
        assert GlobalStrategy.TOTAL_EXPANSIONISM in strategies
        assert GlobalStrategy.COALITION_BUILDER in strategies
        
    def test_distribution_base_n(self):
        """N=4: Should have exactly one of each."""
        engine = SimulationEngine(n_nations=4, map_seed=42)
        strategies = [agent.strategy for agent in engine.agents.values()]
        
        assert len(strategies) == 4
        assert strategies.count(GlobalStrategy.TOTAL_EXPANSIONISM) == 1
        assert strategies.count(GlobalStrategy.COALITION_BUILDER) == 1
        assert strategies.count(GlobalStrategy.ARMED_ISOLATIONISM) == 1
        assert strategies.count(GlobalStrategy.SCORCHED_EARTH) == 1
        
    def test_distribution_large_n(self):
        """N=6: 4 Base + 1 EXP + 1 COAL."""
        engine = SimulationEngine(n_nations=6, map_seed=42)
        strategies = [agent.strategy for agent in engine.agents.values()]
        
        # Base 4
        assert GlobalStrategy.ARMED_ISOLATIONISM in strategies
        assert GlobalStrategy.SCORCHED_EARTH in strategies
        
        # Counts
        # EXP: 1 (Base) + 1 (Fill) = 2
        # COAL: 1 (Base) + 1 (Fill) = 2
        # ISO: 1
        # SCORCHED: 1
        assert strategies.count(GlobalStrategy.TOTAL_EXPANSIONISM) == 2
        assert strategies.count(GlobalStrategy.COALITION_BUILDER) == 2
        assert strategies.count(GlobalStrategy.ARMED_ISOLATIONISM) == 1
        assert strategies.count(GlobalStrategy.SCORCHED_EARTH) == 1

    def test_determinism(self):
        """Same seed yields same distribution."""
        engine1 = SimulationEngine(n_nations=6, map_seed=123)
        strats1 = {id: agent.strategy for id, agent in engine1.agents.items()}
        
        engine2 = SimulationEngine(n_nations=6, map_seed=123)
        strats2 = {id: agent.strategy for id, agent in engine2.agents.items()}
        
        assert strats1 == strats2
        
    def test_randomness(self):
        """Different seeds yield different assignments."""
        # Note: Distribution counts are same, but WHO gets WHAT changes
        engine1 = SimulationEngine(n_nations=6, map_seed=123)
        strats1 = sorted([s.strategy.value for s in engine1.agents.values()]) # Just checking counts here
        
        # We need to check mapping nation_id -> strategy
        mapping1 = {id: agent.strategy for id, agent in engine1.agents.items()}
        
        engine2 = SimulationEngine(n_nations=6, map_seed=456)
        mapping2 = {id: agent.strategy for id, agent in engine2.agents.items()}
        
        # It's possible they match by chance, but unlikely with 6 items
        assert mapping1 != mapping2
