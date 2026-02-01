"""
Tests for Deception Analysis.

Validates deception scoring based on public_intent vs private_intent per domain.
Also tests DeceptionTracker and CoherenceAnalyzer.
"""

import pytest
from conftest import create_test_envelope
from geomas.analysis.deception import (
    DeceptionAnalyzer, 
    DeceptionTracker, 
    CoherenceAnalyzer,
    DeceptionRecord
)
from geomas.agents.schemas import (
    DefenseIntentType, 
    EconomicIntentType, 
    ForeignIntentType,
    GlobalStrategy
)


class TestDeceptionMatrices:
    """Tests for individual domain deception calculations."""
    
    def test_defense_honesty(self):
        """Same public and private intent -> zero deception."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.CONQUEST,
            DefenseIntentType.CONQUEST
        )
        assert score == 0.0
        
    def test_defense_deception_conquest_as_defense(self):
        """Claiming defense when actually conquesting -> high deception."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.CONQUEST,  # private
            DefenseIntentType.DEFENSE      # public
        )
        assert score >= 0.8
        
    def test_defense_deception_idle_as_conquest(self):
        """Claiming conquest when idle (bluffing) -> medium deception."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.IDLE,       # private
            DefenseIntentType.CONQUEST    # public
        )
        assert 0.3 <= score <= 0.5
        
    def test_economic_honesty(self):
        """Same intents -> zero deception."""
        score = DeceptionAnalyzer.calculate_economic_deception(
            EconomicIntentType.GROWTH,
            EconomicIntentType.GROWTH
        )
        assert score == 0.0
        
    def test_economic_sabotage_as_support(self):
        """Claiming support when sabotaging -> maximum deception."""
        score = DeceptionAnalyzer.calculate_economic_deception(
            EconomicIntentType.SABOTAGE,  # private
            EconomicIntentType.SUPPORT    # public
        )
        assert score >= 0.9
        
    def test_foreign_honesty(self):
        """Same intents -> zero deception."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.COOPERATION,
            ForeignIntentType.COOPERATION
        )
        assert score == 0.0
        
    def test_foreign_deception_as_cooperation(self):
        """Claiming cooperation when deceiving -> high deception."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.DECEPTION,    # private
            ForeignIntentType.COOPERATION   # public
        )
        assert score >= 0.9


class TestEnvelopeDeception:
    """Tests for aggregate deception scoring on CountryEnvelope."""
    
    def test_fully_honest_envelope(self):
        """Envelope with matching intents -> zero deception."""
        envelope = create_test_envelope(
            "TEST",
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
            economic_public_intent=EconomicIntentType.GROWTH,
            economic_private_intent=EconomicIntentType.GROWTH,
            foreign_public_intent=ForeignIntentType.COOPERATION,
            foreign_private_intent=ForeignIntentType.COOPERATION,
        )
        
        score = DeceptionAnalyzer.calculate_score(envelope)
        assert score == 0.0
        
    def test_fully_deceptive_envelope(self):
        """Envelope with maximum deception in all domains."""
        envelope = create_test_envelope(
            "TEST",
            defense_public_intent=DefenseIntentType.DEFENSE,
            defense_private_intent=DefenseIntentType.CONQUEST,
            economic_public_intent=EconomicIntentType.SUPPORT,
            economic_private_intent=EconomicIntentType.SABOTAGE,
            foreign_public_intent=ForeignIntentType.COOPERATION,
            foreign_private_intent=ForeignIntentType.DECEPTION,
        )
        
        score = DeceptionAnalyzer.calculate_score(envelope)
        assert score >= 0.8
        
    def test_partial_deception(self):
        """One honest, two deceptive domains."""
        envelope = create_test_envelope(
            "TEST",
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,  # honest
            economic_public_intent=EconomicIntentType.GROWTH,
            economic_private_intent=EconomicIntentType.SABOTAGE,  # deceptive
            foreign_public_intent=ForeignIntentType.COOPERATION,
            foreign_private_intent=ForeignIntentType.COERCION,  # deceptive
        )
        
        score = DeceptionAnalyzer.calculate_score(envelope)
        assert 0.4 <= score <= 0.8


class TestDetailedDeception:
    """Tests for detailed deception breakdown."""
    
    def test_detailed_breakdown(self):
        """Detailed score returns per-domain breakdown."""
        envelope = create_test_envelope(
            "TEST",
            defense_public_intent=DefenseIntentType.DEFENSE,
            defense_private_intent=DefenseIntentType.CONQUEST,  # high deception
            economic_public_intent=EconomicIntentType.IDLE,
            economic_private_intent=EconomicIntentType.IDLE,  # zero deception
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,  # zero deception
        )
        
        result = DeceptionAnalyzer.calculate_detailed_score(envelope)
        
        assert "defense" in result
        assert "economic" in result
        assert "foreign" in result
        assert "total" in result
        
        assert result["defense"] >= 0.8  # high deception
        assert result["economic"] == 0.0  # honest
        assert result["foreign"] == 0.0  # honest
        assert result["total"] == pytest.approx((result["defense"] + 0 + 0) / 3, rel=0.01)


class TestDeceptionTracker:
    """Tests for DeceptionTracker logging and history."""
    
    def test_log_turn_creates_record(self):
        """log_turn creates and returns a DeceptionRecord."""
        tracker = DeceptionTracker()
        envelope = create_test_envelope(
            "nation_1",
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
        )
        
        record = tracker.log_turn(envelope)
        
        assert isinstance(record, DeceptionRecord)
        assert record.nation_id == "nation_1"
        assert record.turn == 1
        assert record.total_deception == 0.0  # All honest
        
    def test_get_nation_history(self):
        """History accumulates across turns."""
        tracker = DeceptionTracker()
        
        # Log multiple turns
        for turn in range(1, 4):
            envelope = create_test_envelope(
                "nation_1",
                turn=turn,
                defense_public_intent=DefenseIntentType.IDLE,
                defense_private_intent=DefenseIntentType.IDLE,
            )
            tracker.log_turn(envelope)
        
        history = tracker.get_nation_history("nation_1")
        assert len(history) == 3
        assert [r.turn for r in history] == [1, 2, 3]
        
    def test_get_turn_summary(self):
        """Turn summary returns all nations for a turn."""
        tracker = DeceptionTracker()
        
        # Log same turn for two nations
        for nation_id in ["nation_1", "nation_2"]:
            envelope = create_test_envelope(
                nation_id,
                defense_public_intent=DefenseIntentType.IDLE,
                defense_private_intent=DefenseIntentType.IDLE,
            )
            tracker.log_turn(envelope)
        
        summary = tracker.get_turn_summary(1)
        assert len(summary) == 2
        assert "nation_1" in summary
        assert "nation_2" in summary
        
    def test_get_nation_average(self):
        """Average scores are calculated correctly."""
        tracker = DeceptionTracker()
        
        # Turn 1: Honest
        env1 = create_test_envelope(
            "nation_1",
            turn=1,
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
            economic_public_intent=EconomicIntentType.IDLE,
            economic_private_intent=EconomicIntentType.IDLE,
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
        )
        tracker.log_turn(env1)
        
        # Turn 2: Deceptive in defense (0.9)
        env2 = create_test_envelope(
            "nation_1",
            turn=2,
            defense_public_intent=DefenseIntentType.DEFENSE,
            defense_private_intent=DefenseIntentType.CONQUEST,  # 0.9 deception
            economic_public_intent=EconomicIntentType.IDLE,
            economic_private_intent=EconomicIntentType.IDLE,
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
        )
        tracker.log_turn(env2)
        
        avg = tracker.get_nation_average("nation_1")
        assert "defense" in avg
        assert "economic" in avg
        assert "foreign" in avg
        assert "total" in avg
        assert "coherence" in avg
        
        # Defense average should be (0.0 + 0.9) / 2 = 0.45
        assert avg["defense"] == pytest.approx(0.45, rel=0.01)
        
    def test_most_deceptive_nations(self):
        """Ranking of most deceptive nations works."""
        tracker = DeceptionTracker()
        
        # Nation 1: Honest
        env1 = create_test_envelope(
            "honest_nation",
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
            economic_public_intent=EconomicIntentType.IDLE,
            economic_private_intent=EconomicIntentType.IDLE,
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
        )
        tracker.log_turn(env1)
        
        # Nation 2: Very deceptive
        env2 = create_test_envelope(
            "deceptive_nation",
            defense_public_intent=DefenseIntentType.DEFENSE,
            defense_private_intent=DefenseIntentType.CONQUEST,
            economic_public_intent=EconomicIntentType.SUPPORT,
            economic_private_intent=EconomicIntentType.SABOTAGE,
            foreign_public_intent=ForeignIntentType.COOPERATION,
            foreign_private_intent=ForeignIntentType.DECEPTION,
        )
        tracker.log_turn(env2)
        
        ranking = tracker.get_most_deceptive_nations(limit=5)
        assert len(ranking) == 2
        assert ranking[0][0] == "deceptive_nation"  # Most deceptive first
        assert ranking[1][0] == "honest_nation"


class TestCoherenceAnalyzer:
    """Tests for Strategic Coherence scoring."""
    
    def test_perfect_coherence_expansionist(self):
        """TOTAL_EXPANSIONISM with matching intents -> 1.0 coherence."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.CONQUEST,        # Expected
            EconomicIntentType.GROWTH,          # Expected
            ForeignIntentType.COERCION          # Expected
        )
        assert score == 1.0
        
    def test_perfect_coherence_coalition(self):
        """COALITION_BUILDER with matching intents -> 1.0 coherence."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.COALITION_BUILDER,
            DefenseIntentType.DEFENSE,          # Expected
            EconomicIntentType.SUPPORT,         # Expected
            ForeignIntentType.COOPERATION       # Expected
        )
        assert score == 1.0
        
    def test_zero_coherence(self):
        """Completely misaligned intents -> 0.0 coherence."""
        # TOTAL_EXPANSIONISM expects CONQUEST, GROWTH/SABOTAGE, COERCION/DECEPTION
        # We give complete opposites
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.IDLE,             # Not expected
            EconomicIntentType.SUPPORT,         # Not expected
            ForeignIntentType.COOPERATION       # Not expected
        )
        assert score == 0.0
        
    def test_partial_coherence(self):
        """Some matching intents -> partial coherence."""
        # DOMESTIC_RECOVERY expects DEFENSE/IDLE, SURVIVAL/GROWTH, APPEASEMENT/IDLE
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.DOMESTIC_RECOVERY,
            DefenseIntentType.DEFENSE,          # Match
            EconomicIntentType.SURVIVAL,        # Match
            ForeignIntentType.COERCION          # No match
        )
        # 2 out of 3 matches
        assert score == pytest.approx(2/3, rel=0.01)
        
    def test_coherence_in_deception_record(self):
        """Tracker includes coherence in records."""
        tracker = DeceptionTracker()
        
        # COALITION_BUILDER with perfectly coherent intents
        envelope = create_test_envelope(
            "nation_1",
            global_strategy=GlobalStrategy.COALITION_BUILDER,
            defense_private_intent=DefenseIntentType.DEFENSE,
            economic_private_intent=EconomicIntentType.SUPPORT,
            foreign_private_intent=ForeignIntentType.COOPERATION,
        )
        
        record = tracker.log_turn(envelope)
        assert record.coherence_score == 1.0

