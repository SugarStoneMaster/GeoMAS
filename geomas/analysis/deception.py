"""
Deception Analysis - Core Analyzer.

Calculates deception scores by comparing public_intent vs private_intent per domain.
"""

from geomas.agents.schemas import (
    CountryEnvelope, 
    DefenseIntentType, 
    EconomicIntentType, 
    ForeignIntentType
)


class DeceptionAnalyzer:
    """
    Calculates Deception Scores by comparing Public Intent vs Private Intent.
    
    Score range: 0.0 (Honest - same intent) to 1.0 (Maximum deception).
    
    Deception is calculated per-domain, then aggregated.
    """

    # --- DEFENSE DOMAIN DECEPTION MATRIX ---
    # Key: (private_intent, public_intent) -> deception score
    DEFENSE_MATRIX = {
        # Private is CONQUEST
        (DefenseIntentType.CONQUEST, DefenseIntentType.CONQUEST): 0.0,
        (DefenseIntentType.CONQUEST, DefenseIntentType.DEFENSE): 0.9,
        (DefenseIntentType.CONQUEST, DefenseIntentType.DETERRENCE): 0.7,
        (DefenseIntentType.CONQUEST, DefenseIntentType.IDLE): 0.95,  # Increased from 0.8 (Sneak Attack)

        # Private is DEFENSE
        (DefenseIntentType.DEFENSE, DefenseIntentType.DEFENSE): 0.0,
        (DefenseIntentType.DEFENSE, DefenseIntentType.CONQUEST): 0.2,
        (DefenseIntentType.DEFENSE, DefenseIntentType.DETERRENCE): 0.1,
        (DefenseIntentType.DEFENSE, DefenseIntentType.IDLE): 0.3,

        # Private is DETERRENCE
        (DefenseIntentType.DETERRENCE, DefenseIntentType.DETERRENCE): 0.0,
        (DefenseIntentType.DETERRENCE, DefenseIntentType.CONQUEST): 0.3,
        (DefenseIntentType.DETERRENCE, DefenseIntentType.DEFENSE): 0.1,
        (DefenseIntentType.DETERRENCE, DefenseIntentType.IDLE): 0.2,

        # Private is IDLE
        (DefenseIntentType.IDLE, DefenseIntentType.IDLE): 0.0,
        (DefenseIntentType.IDLE, DefenseIntentType.CONQUEST): 0.8,  # Increased from 0.4 (Bluff)
        (DefenseIntentType.IDLE, DefenseIntentType.DEFENSE): 0.5,   # Increased from 0.2 (Fake Defense)
        (DefenseIntentType.IDLE, DefenseIntentType.DETERRENCE): 0.6, # Increased from 0.2 (Bluff)
    }
    
    # --- ECONOMIC DOMAIN DECEPTION MATRIX ---
    ECONOMIC_MATRIX = {
        # Private is GROWTH
        (EconomicIntentType.GROWTH, EconomicIntentType.GROWTH): 0.0,
        (EconomicIntentType.GROWTH, EconomicIntentType.SUPPORT): 0.2,
        (EconomicIntentType.GROWTH, EconomicIntentType.SURVIVAL): 0.2,
        (EconomicIntentType.GROWTH, EconomicIntentType.IDLE): 0.1,
        
        # Private is SUPPORT
        (EconomicIntentType.SUPPORT, EconomicIntentType.SUPPORT): 0.0,
        (EconomicIntentType.SUPPORT, EconomicIntentType.GROWTH): 0.1,
        (EconomicIntentType.SUPPORT, EconomicIntentType.SURVIVAL): 0.2,
        (EconomicIntentType.SUPPORT, EconomicIntentType.IDLE): 0.2,
        
        # Private is SURVIVAL
        (EconomicIntentType.SURVIVAL, EconomicIntentType.SURVIVAL): 0.0,
        (EconomicIntentType.SURVIVAL, EconomicIntentType.GROWTH): 0.4,
        (EconomicIntentType.SURVIVAL, EconomicIntentType.SUPPORT): 0.3,
        (EconomicIntentType.SURVIVAL, EconomicIntentType.IDLE): 0.2,
        
        # Private is IDLE
        (EconomicIntentType.IDLE, EconomicIntentType.IDLE): 0.0,
        (EconomicIntentType.IDLE, EconomicIntentType.GROWTH): 0.2,
        (EconomicIntentType.IDLE, EconomicIntentType.SUPPORT): 0.2,
        (EconomicIntentType.IDLE, EconomicIntentType.SURVIVAL): 0.1,
    }
    
    # --- FOREIGN DOMAIN DECEPTION MATRIX ---
    FOREIGN_MATRIX = {
        # Private is DECEPTION
        (ForeignIntentType.DECEPTION, ForeignIntentType.DECEPTION): 0.0,
        (ForeignIntentType.DECEPTION, ForeignIntentType.COOPERATION): 0.95,
        (ForeignIntentType.DECEPTION, ForeignIntentType.APPEASEMENT): 0.7,
        (ForeignIntentType.DECEPTION, ForeignIntentType.COERCION): 0.4,
        (ForeignIntentType.DECEPTION, ForeignIntentType.IDLE): 0.5,
        
        # Private is COERCION
        (ForeignIntentType.COERCION, ForeignIntentType.COERCION): 0.0,
        (ForeignIntentType.COERCION, ForeignIntentType.COOPERATION): 0.85,
        (ForeignIntentType.COERCION, ForeignIntentType.APPEASEMENT): 0.6,
        (ForeignIntentType.COERCION, ForeignIntentType.DECEPTION): 0.2,
        (ForeignIntentType.COERCION, ForeignIntentType.IDLE): 0.4,
        
        # Private is COOPERATION
        (ForeignIntentType.COOPERATION, ForeignIntentType.COOPERATION): 0.0,
        (ForeignIntentType.COOPERATION, ForeignIntentType.COERCION): 0.3,
        (ForeignIntentType.COOPERATION, ForeignIntentType.APPEASEMENT): 0.1,
        (ForeignIntentType.COOPERATION, ForeignIntentType.DECEPTION): 0.3,
        (ForeignIntentType.COOPERATION, ForeignIntentType.IDLE): 0.1,
        
        # Private is APPEASEMENT
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.APPEASEMENT): 0.0,
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.COOPERATION): 0.1,
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.COERCION): 0.5,
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.DECEPTION): 0.3,
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.IDLE): 0.2,
        
        # Private is IDLE
        (ForeignIntentType.IDLE, ForeignIntentType.IDLE): 0.0,
        (ForeignIntentType.IDLE, ForeignIntentType.COOPERATION): 0.2,
        (ForeignIntentType.IDLE, ForeignIntentType.COERCION): 0.3,
        (ForeignIntentType.IDLE, ForeignIntentType.APPEASEMENT): 0.1,
        (ForeignIntentType.IDLE, ForeignIntentType.DECEPTION): 0.2,
    }

    @classmethod
    def calculate_defense_deception(
        cls, 
        private_intent: DefenseIntentType, 
        public_intent: DefenseIntentType
    ) -> float:
        """Calculate deception score for defense domain."""
        return cls.DEFENSE_MATRIX.get((private_intent, public_intent), 0.5)
    
    @classmethod
    def calculate_economic_deception(
        cls, 
        private_intent: EconomicIntentType, 
        public_intent: EconomicIntentType
    ) -> float:
        """Calculate deception score for economic domain."""
        return cls.ECONOMIC_MATRIX.get((private_intent, public_intent), 0.5)
    
    @classmethod
    def calculate_foreign_deception(
        cls, 
        private_intent: ForeignIntentType, 
        public_intent: ForeignIntentType
    ) -> float:
        """Calculate deception score for foreign domain."""
        return cls.FOREIGN_MATRIX.get((private_intent, public_intent), 0.5)

    @classmethod
    def calculate_score(cls, envelope: CountryEnvelope) -> float:
        """
        Calculate aggregated deception score for an envelope.
        
        Returns the average of domain-specific deception scores.
        
        Returns:
            float: 0.0 (honest) to 1.0 (maximum deception)
        """
        defense_score = cls.calculate_defense_deception(
            envelope.defense_private_intent,
            envelope.defense_public_intent
        )
        economic_score = cls.calculate_economic_deception(
            envelope.economic_private_intent,
            envelope.economic_public_intent
        )
        foreign_score = cls.calculate_foreign_deception(
            envelope.foreign_private_intent,
            envelope.foreign_public_intent
        )
        
        return (defense_score + economic_score + foreign_score) / 3.0
    
    @classmethod
    def calculate_detailed_score(cls, envelope: CountryEnvelope) -> dict:
        """
        Calculate detailed deception breakdown by domain.
        
        Returns:
            dict with keys: defense, economic, foreign, total
        """
        defense_score = cls.calculate_defense_deception(
            envelope.defense_private_intent,
            envelope.defense_public_intent
        )
        economic_score = cls.calculate_economic_deception(
            envelope.economic_private_intent,
            envelope.economic_public_intent
        )
        foreign_score = cls.calculate_foreign_deception(
            envelope.foreign_private_intent,
            envelope.foreign_public_intent
        )
        
        return {
            "defense": defense_score,
            "economic": economic_score,
            "foreign": foreign_score,
            "total": (defense_score + economic_score + foreign_score) / 3.0
        }
