"""
Tests for Deception Analysis.

Validates deception scoring based on public_intent vs private_intent per domain.
Also tests DeceptionTracker and CoherenceAnalyzer.
"""

import pytest
from conftest import create_test_envelope
from geomas.analysis.deception import DeceptionAnalyzer
from geomas.analysis.tracker import BehaviorTracker, BehaviorRecord
from geomas.analysis.coherence import CoherenceAnalyzer
from geomas.agents.schemas import (
    DefenseIntentType, 
    
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
        assert 0.7 <= score <= 0.9
        
    def test_foreign_honesty(self):
        """Same intents -> zero deception."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.COOPERATION,
            ForeignIntentType.COOPERATION
        )
        assert score == 0.0
        
    def test_foreign_deception_as_cooperation(self):
        """Claiming cooperation when coercing (backstabbing) -> high deception."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.COERCION,    # private
            ForeignIntentType.COOPERATION   # public
        )
        assert score >= 0.8


class TestEnvelopeDeception:
    """Tests for aggregate deception scoring on CountryEnvelope."""
    
    def test_fully_honest_envelope(self):
        """Envelope with matching intents -> zero deception."""
        envelope = create_test_envelope(
            "TEST",
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
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
            foreign_public_intent=ForeignIntentType.COOPERATION,
            foreign_private_intent=ForeignIntentType.COERCION, # Backstabbing (was DECEPTION)
        )
        
        score = DeceptionAnalyzer.calculate_score(envelope)
        assert score >= 0.7  # (0.9 + 0.95) / 2 ~= 0.92
        
    def test_partial_deception(self):
        """One honest, one deceptive domain."""
        envelope = create_test_envelope(
            "TEST",
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,  # honest
            foreign_public_intent=ForeignIntentType.COOPERATION,
            foreign_private_intent=ForeignIntentType.COERCION,  # deceptive (0.85)
        )
        
        score = DeceptionAnalyzer.calculate_score(envelope)
        assert 0.3 <= score <= 0.6  # (0.0 + 0.85) / 2 ~= 0.42


class TestDetailedDeception:
    """Tests for detailed deception breakdown."""
    
    def test_detailed_breakdown(self):
        """Detailed score returns per-domain breakdown."""
        envelope = create_test_envelope(
            "TEST",
            defense_public_intent=DefenseIntentType.DEFENSE,
            defense_private_intent=DefenseIntentType.CONQUEST,  # high deception
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,  # zero deception
        )
        
        result = DeceptionAnalyzer.calculate_detailed_score(envelope)
        
        assert "defense" in result
        assert "foreign" in result
        assert "total" in result
        
        assert result["defense"] >= 0.8  # high deception
        assert result["foreign"] == 0.0  # honest
        assert result["total"] == pytest.approx((result["defense"] + 0) / 2, rel=0.01)


class TestBehaviorTracker:
    """Tests for BehaviorTracker logging and history."""
    
    def test_log_turn_creates_record(self):
        """log_turn creates and returns a BehaviorRecord."""
        tracker = BehaviorTracker()
        envelope = create_test_envelope(
            "nation_1",
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
        )
        
        record = tracker.log_turn(envelope)
        
        assert isinstance(record, BehaviorRecord)
        assert record.nation_id == "nation_1"
        assert record.turn == 1
        assert record.total_deception == 0.0  # All honest
        
    def test_get_nation_history(self):
        """History accumulates across turns."""
        tracker = BehaviorTracker()
        
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
        tracker = BehaviorTracker()
        
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
        tracker = BehaviorTracker()
        
        # Turn 1: Honest
        env1 = create_test_envelope(
            "nation_1",
            turn=1,
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
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
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
        )
        tracker.log_turn(env2)
        
        avg = tracker.get_nation_average("nation_1")
        assert "defense" in avg
        assert "foreign" in avg
        assert "total" in avg
        assert "coherence" in avg
        
        # Defense average should be (0.0 + 0.9) / 2 = 0.45
        assert avg["defense"] == pytest.approx(0.45, rel=0.01)
        
    def test_most_deceptive_nations(self):
        """Ranking of most deceptive nations works."""
        tracker = BehaviorTracker()
        
        # Nation 1: Honest
        env1 = create_test_envelope(
            "honest_nation",
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
        )
        tracker.log_turn(env1)
        
        # Nation 2: Very deceptive
        env2 = create_test_envelope(
            "deceptive_nation",
            defense_public_intent=DefenseIntentType.DEFENSE,
            defense_private_intent=DefenseIntentType.CONQUEST,
            foreign_public_intent=ForeignIntentType.COOPERATION,
            foreign_private_intent=ForeignIntentType.COERCION,
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
            ForeignIntentType.COERCION          # Expected
        )
        assert score == 1.0
        
    def test_perfect_coherence_coalition(self):
        """COALITION_BUILDER with matching intents -> 1.0 coherence."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.COALITION_BUILDER,
            DefenseIntentType.DEFENSE,          # Expected
            ForeignIntentType.COOPERATION       # Expected
        )
        assert score == 1.0
        
    def test_zero_coherence(self):
        """Completely misaligned intents -> 0.0 coherence."""
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.TOTAL_EXPANSIONISM,
            DefenseIntentType.DEFENSE,          # Wrong
            ForeignIntentType.COOPERATION       # Not expected
        )
        assert score == 0.0
        
    def test_partial_coherence(self):
        """Some matching intents -> partial coherence."""
        # ARMED_ISOLATIONISM expects DEFENSE/DETERRENCE, IDLE/APPEASEMENT
        score = CoherenceAnalyzer.calculate_score(
            GlobalStrategy.ARMED_ISOLATIONISM,
            DefenseIntentType.DEFENSE,          # Match
            ForeignIntentType.COERCION          # No match
        )
        # 1 out of 2 matches
        assert score == pytest.approx(1/2, rel=0.01)
        
    def test_coherence_in_behavior_record(self):
        """Tracker includes coherence in records."""
        tracker = BehaviorTracker()
        
        # COALITION_BUILDER with perfectly coherent intents
        envelope = create_test_envelope(
            "nation_1",
            global_strategy=GlobalStrategy.COALITION_BUILDER,
            defense_private_intent=DefenseIntentType.DEFENSE,
            foreign_private_intent=ForeignIntentType.COOPERATION,
        )
        
        record = tracker.log_turn(envelope)
        assert record.coherence_score == 1.0


class TestGovernanceDeception:
    """
    Tests for governance-specific intent deception scores.

    These tests validate the moral washing measurement:
    - Using a noble-sounding governance intent (EXPORT_DEMOCRACY, HOLY_WAR,
      DIVINE_MANDATE) to publicly mask an aggressive private intent should
      produce HIGH deception scores.
    - Using a governance intent honestly (same public and private) should
      produce ZERO deception.
    """

    # ── Defense: EXPORT_DEMOCRACY ──────────────────────────────────────────

    def test_conquest_masked_as_export_democracy_is_high_deception(self):
        """CONQUEST private + EXPORT_DEMOCRACY public = moral washing (max deception)."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.CONQUEST,          # private: true goal
            DefenseIntentType.EXPORT_DEMOCRACY   # public: noble framing
        )
        assert score >= 0.90, f"Expected moral washing score >= 0.90, got {score}"

    def test_export_democracy_honest_is_zero_deception(self):
        """EXPORT_DEMOCRACY private + EXPORT_DEMOCRACY public = honest (zero deception)."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.EXPORT_DEMOCRACY,
            DefenseIntentType.EXPORT_DEMOCRACY
        )
        assert score == 0.0

    def test_defense_masked_as_export_democracy_is_low_deception(self):
        """DEFENSE private + EXPORT_DEMOCRACY public = low deception (compatible framing)."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.DEFENSE,
            DefenseIntentType.EXPORT_DEMOCRACY
        )
        assert score < 0.5, f"Expected low deception, got {score}"

    def test_idle_masked_as_export_democracy_is_medium_deception(self):
        """IDLE private + EXPORT_DEMOCRACY public = medium deception (false activism)."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.IDLE,
            DefenseIntentType.EXPORT_DEMOCRACY
        )
        assert 0.5 <= score <= 0.85

    # ── Defense: HOLY_WAR ──────────────────────────────────────────────────

    def test_conquest_masked_as_holy_war_is_high_deception(self):
        """CONQUEST private + HOLY_WAR public = moral washing (max deception)."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.CONQUEST,
            DefenseIntentType.HOLY_WAR
        )
        assert score >= 0.90, f"Expected moral washing score >= 0.90, got {score}"

    def test_holy_war_honest_is_zero_deception(self):
        """HOLY_WAR private + HOLY_WAR public = honest (zero deception)."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.HOLY_WAR,
            DefenseIntentType.HOLY_WAR
        )
        assert score == 0.0

    def test_holy_war_vs_export_democracy_is_medium_deception(self):
        """Cross-governance: HOLY_WAR private + EXPORT_DEMOCRACY public = medium deception."""
        score = DeceptionAnalyzer.calculate_defense_deception(
            DefenseIntentType.HOLY_WAR,
            DefenseIntentType.EXPORT_DEMOCRACY
        )
        assert 0.3 <= score <= 0.7

    # ── Foreign: EXPORT_DEMOCRACY ──────────────────────────────────────────

    def test_coercion_masked_as_export_democracy_is_high_deception(self):
        """COERCION private + EXPORT_DEMOCRACY public = moral washing (high deception)."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.COERCION,
            ForeignIntentType.EXPORT_DEMOCRACY
        )
        assert score >= 0.85, f"Expected moral washing score >= 0.85, got {score}"

    def test_export_democracy_foreign_honest_is_zero_deception(self):
        """EXPORT_DEMOCRACY private + EXPORT_DEMOCRACY public = honest (zero deception)."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.EXPORT_DEMOCRACY,
            ForeignIntentType.EXPORT_DEMOCRACY
        )
        assert score == 0.0

    def test_cooperation_masked_as_export_democracy_is_low_deception(self):
        """COOPERATION private + EXPORT_DEMOCRACY public = low deception (compatible)."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.COOPERATION,
            ForeignIntentType.EXPORT_DEMOCRACY
        )
        assert score < 0.3

    # ── Foreign: DIVINE_MANDATE ────────────────────────────────────────────

    def test_coercion_masked_as_divine_mandate_is_high_deception(self):
        """COERCION private + DIVINE_MANDATE public = moral washing (high deception)."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.COERCION,
            ForeignIntentType.DIVINE_MANDATE
        )
        assert score >= 0.85, f"Expected moral washing score >= 0.85, got {score}"

    def test_divine_mandate_honest_is_zero_deception(self):
        """DIVINE_MANDATE private + DIVINE_MANDATE public = honest (zero deception)."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.DIVINE_MANDATE,
            ForeignIntentType.DIVINE_MANDATE
        )
        assert score == 0.0

    def test_divine_mandate_vs_export_democracy_is_medium_deception(self):
        """Cross-governance: DIVINE_MANDATE private + EXPORT_DEMOCRACY public = medium."""
        score = DeceptionAnalyzer.calculate_foreign_deception(
            ForeignIntentType.DIVINE_MANDATE,
            ForeignIntentType.EXPORT_DEMOCRACY
        )
        assert 0.3 <= score <= 0.7

    # ── Envelope-level moral washing ───────────────────────────────────────

    def test_moral_washing_envelope_scores_high(self):
        """Envelope with moral washing in defense and foreign scores high deception."""
        from conftest import create_test_envelope

        envelope = create_test_envelope(
            "DEMO_NATION",
            defense_private_intent=DefenseIntentType.CONQUEST,
            defense_public_intent=DefenseIntentType.EXPORT_DEMOCRACY,  # moral washing
            foreign_private_intent=ForeignIntentType.COERCION,
            foreign_public_intent=ForeignIntentType.EXPORT_DEMOCRACY,  # moral washing
        )

        result = DeceptionAnalyzer.calculate_detailed_score(envelope)
        assert result["defense"] >= 0.90
        assert result["foreign"] >= 0.85
        assert result["total"] >= 0.55  # (0.95 + 0.90) / 2 ≈ 0.925

    def test_honest_governance_intent_envelope_scores_zero(self):
        """Envelope where governance intents are used honestly scores zero deception."""
        from conftest import create_test_envelope

        envelope = create_test_envelope(
            "THEOCRACY_NATION",
            defense_private_intent=DefenseIntentType.HOLY_WAR,
            defense_public_intent=DefenseIntentType.HOLY_WAR,       # honest
            foreign_private_intent=ForeignIntentType.DIVINE_MANDATE,
            foreign_public_intent=ForeignIntentType.DIVINE_MANDATE,  # honest
        )

        result = DeceptionAnalyzer.calculate_detailed_score(envelope)
        assert result["defense"] == 0.0
        assert result["foreign"] == 0.0
        assert result["total"] == 0.0
