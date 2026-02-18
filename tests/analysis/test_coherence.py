"""
Tests for Coherence Analyzer.

Tests coherence scoring for all GlobalStrategy types.
Economic intent removed: coherence is now measured on defense + foreign only.
"""

import pytest
from geomas.analysis.coherence import CoherenceAnalyzer
from geomas.agents.schemas import (
    GlobalStrategy,
    DefenseIntentType,
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
        """Perfect coherence with conquest + coercion."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.CONQUEST,
            ForeignIntentType.COERCION
        )
        assert score == 1.0
    
    def test_partial_coherence(self):
        """Partial coherence with only defense matching."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.CONQUEST,  # Match
            ForeignIntentType.COOPERATION  # No match
        )
        assert score == pytest.approx(1/2)
    
    def test_incoherent(self):
        """Zero coherence with completely wrong intents."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.DEFENSE,  # Wrong
            ForeignIntentType.APPEASEMENT  # Wrong
        )
        assert score == 0.0


class TestArmedIsolationism:
    """Tests for ARMED_ISOLATIONISM strategy coherence."""
    
    def test_perfect_coherence(self):
        """Perfect coherence with defense + idle diplomacy."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.ARMED_ISOLATIONISM,
            DefenseIntentType.DEFENSE,
            ForeignIntentType.IDLE
        )
        assert score == 1.0
    
    def test_deterrence_also_valid(self):
        """Deterrence is also valid for defense in isolation."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.ARMED_ISOLATIONISM,
            DefenseIntentType.DETERRENCE,
            ForeignIntentType.APPEASEMENT
        )
        assert score == 1.0


class TestCoalitionBuilder:
    """Tests for COALITION_BUILDER strategy coherence."""
    
    def test_perfect_coherence(self):
        """Perfect coherence with defense + cooperation."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.COALITION_BUILDER,
            DefenseIntentType.DEFENSE,
            ForeignIntentType.COOPERATION
        )
        assert score == 1.0
    
    def test_deterrence_valid_for_coalition(self):
        """Deterrence valid for protecting coalition."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.COALITION_BUILDER,
            DefenseIntentType.DETERRENCE,
            ForeignIntentType.COOPERATION
        )
        assert score == 1.0


class TestScorchedEarth:
    """Tests for SCORCHED_EARTH strategy coherence."""
    
    def test_perfect_coherence(self):
        """Perfect coherence with conquest + coercion."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.SCORCHED_EARTH,
            DefenseIntentType.CONQUEST,
            ForeignIntentType.COERCION
        )
        assert score == 1.0
    
    def test_conquest_valid(self):
        """Conquest is valid for scorched earth."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.SCORCHED_EARTH,
            DefenseIntentType.CONQUEST,
            ForeignIntentType.COERCION
        )
        assert score == 1.0


class TestScoreInterpretation:
    """Tests for interpreting coherence scores."""
    
    def test_score_of_half(self):
        """0.5 score means 1 of 2 intents match."""
        # For COALITION_BUILDER: defense or deterrence, cooperation
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.COALITION_BUILDER,
            DefenseIntentType.CONQUEST,  # Wrong
            ForeignIntentType.COOPERATION  # Match
        )
        assert score == pytest.approx(1/2)
    
    def test_score_of_zero(self):
        """0.0 score means no intents match."""
        # SCORCHED_EARTH expects CONQUEST/DEFENSE/DETERRENCE, COERCION/DIVINE_MANDATE
        # DEFENSE is valid for SCORCHED_EARTH, COOPERATION is not
        # Use TOTAL_EXPANSIONISM: expects CONQUEST/DETERRENCE/IDLE/EXPORT_DEMOCRACY/HOLY_WAR, COERCION/IDLE/EXPORT_DEMOCRACY/DIVINE_MANDATE
        # DEFENSE is NOT in TOTAL_EXPANSIONISM defense pool, APPEASEMENT is NOT in foreign pool
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.DEFENSE,   # Wrong: not in TOTAL_EXPANSIONISM defense pool
            ForeignIntentType.APPEASEMENT  # Wrong: not in TOTAL_EXPANSIONISM foreign pool
        )
        assert score == 0.0
