"""
Tests for Deception Analysis.

Validates deception scoring based on public_intent vs private_intent per domain.
"""

import pytest
from conftest import create_test_envelope
from geomas.analysis.deception import DeceptionAnalyzer
from geomas.agents.schemas import DefenseIntentType, EconomicIntentType, ForeignIntentType


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
