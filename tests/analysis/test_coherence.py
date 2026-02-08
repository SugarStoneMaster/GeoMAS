"""
Tests for Coherence Analyzer.

Tests coherence scoring for all 7 GlobalStrategy types.
"""

import pytest
from geomas.analysis.coherence import CoherenceAnalyzer
from geomas.agents.schemas import (
    GlobalStrategy,
    DefenseIntentType,
    EconomicIntentType,
    ForeignIntentType,
)


class TestCoherenceAnalyzerBasics:
    """Basic tests for CoherenceAnalyzer."""
    
    def test_returns_float_between_0_and_1(self):
        """Score is always between 0.0 and 1.0."""
        for strategy in GlobalStrategy:
            score = CoherenceAnalyzer.calculate_score(
                strategy,
                DefenseIntentType.DEFENSE,
                EconomicIntentType.GROWTH,
                ForeignIntentType.COOPERATION
            )
            assert 0.0 <= score <= 1.0
    
    def test_all_strategies_have_expected_intents(self):
        """All strategies are defined in EXPECTED_INTENTS mapping."""
        for strategy in GlobalStrategy:
            assert strategy in CoherenceAnalyzer.EXPECTED_INTENTS


class TestTotalExpansionism:
    """Tests for TOTAL_EXPANSIONISM strategy coherence."""
    
    def test_perfect_coherence(self):
        """Perfect coherence with conquest + growth + coercion."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.CONQUEST,
            EconomicIntentType.GROWTH,
            ForeignIntentType.COERCION
        )
        assert score == 1.0
    
    def test_partial_coherence(self):
        """Partial coherence with some matching intents."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.CONQUEST,  # Match
            EconomicIntentType.SURVIVAL,  # No match
            ForeignIntentType.COOPERATION  # No match
        )
        assert score == pytest.approx(1/3)
    
    def test_incoherent(self):
        """Zero coherence with completely wrong intents."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.IDLE,  # Wrong
            EconomicIntentType.SURVIVAL,  # Wrong
            ForeignIntentType.APPEASEMENT  # Wrong
        )
        assert score == 0.0


class TestArmedIsolationism:
    """Tests for ARMED_ISOLATIONISM strategy coherence."""
    
    def test_perfect_coherence(self):
        """Perfect coherence with defense + growth + idle diplomacy."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.ARMED_ISOLATIONISM,
            DefenseIntentType.DEFENSE,
            EconomicIntentType.GROWTH,
            ForeignIntentType.IDLE
        )
        assert score == 1.0
    
    def test_deterrence_also_valid(self):
        """Deterrence is also valid for defense in isolation."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.ARMED_ISOLATIONISM,
            DefenseIntentType.DETERRENCE,
            EconomicIntentType.SURVIVAL,
            ForeignIntentType.APPEASEMENT
        )
        assert score == 1.0

class TestMercantileHegemony:
    """Tests for MERCANTILE_HEGEMONY strategy coherence."""
    
    def test_perfect_coherence(self):
        """Perfect coherence with deterrence + growth + cooperation."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.MERCANTILE_HEGEMONY,
            DefenseIntentType.DETERRENCE,
            EconomicIntentType.GROWTH,
            ForeignIntentType.COOPERATION
        )
        assert score == 1.0
    
    def test_support_economy_valid(self):
        """Support is valid economic intent for mercantile hegemony."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.MERCANTILE_HEGEMONY,
            DefenseIntentType.IDLE,
            EconomicIntentType.SUPPORT,
            ForeignIntentType.COERCION
        )
        assert score == 1.0


class TestDomesticRecovery:
    """Tests for DOMESTIC_RECOVERY strategy coherence."""
    
    def test_perfect_coherence(self):
        """Perfect coherence with defense + survival + appeasement."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.DOMESTIC_RECOVERY,
            DefenseIntentType.DEFENSE,
            EconomicIntentType.SURVIVAL,
            ForeignIntentType.APPEASEMENT
        )
        assert score == 1.0
    
    def test_growth_also_acceptable(self):
        """Growth is acceptable for recovery strategy."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.DOMESTIC_RECOVERY,
            DefenseIntentType.IDLE,
            EconomicIntentType.GROWTH,
            ForeignIntentType.IDLE
        )
        assert score == 1.0


class TestCoalitionBuilder:
    """Tests for COALITION_BUILDER strategy coherence."""
    
    def test_perfect_coherence(self):
        """Perfect coherence with defense + support + cooperation."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.COALITION_BUILDER,
            DefenseIntentType.DEFENSE,
            EconomicIntentType.SUPPORT,
            ForeignIntentType.COOPERATION
        )
        assert score == 1.0
    
    def test_deterrence_valid_for_coalition(self):
        """Deterrence valid for protecting coalition."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.COALITION_BUILDER,
            DefenseIntentType.DETERRENCE,
            EconomicIntentType.GROWTH,
            ForeignIntentType.COOPERATION
        )
        assert score == 1.0


class TestScorchedEarth:
    """Tests for SCORCHED_EARTH strategy coherence."""
    
    def test_perfect_coherence(self):
        """Perfect coherence with conquest + survival + coercion."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.SCORCHED_EARTH,
            DefenseIntentType.CONQUEST,
            EconomicIntentType.SURVIVAL,
            ForeignIntentType.COERCION
        )
        assert score == 1.0
    
    def test_punishment_valid(self):
        """Punishment is valid for scorched earth."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.SCORCHED_EARTH,
            DefenseIntentType.PUNISHMENT,
            EconomicIntentType.SURVIVAL,
            ForeignIntentType.DECEPTION
        )
        assert score == 1.0


class TestScoreInterpretation:
    """Tests for interpreting coherence scores."""
    
    def test_score_of_one_third(self):
        """1/3 score means 1 of 3 intents match."""
        # For COALITION_BUILDER: defense or deterrence, support or growth, cooperation
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.COALITION_BUILDER,
            DefenseIntentType.CONQUEST,  # Wrong
            EconomicIntentType.SURVIVAL,  # Wrong
            ForeignIntentType.COOPERATION  # Match
        )
        assert score == pytest.approx(1/3)
    
    def test_score_of_two_thirds(self):
        """2/3 score means 2 of 3 intents match."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.COALITION_BUILDER,
            DefenseIntentType.DEFENSE,  # Match
            EconomicIntentType.SURVIVAL,  # Wrong
            ForeignIntentType.COOPERATION  # Match
        )
        assert score == pytest.approx(2/3)
