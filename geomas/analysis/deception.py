"""
Deception Analysis - Core Analyzer.

Calculates deception scores by comparing public_intent vs private_intent per domain.
"""

from geomas.agents.schemas import (
    CountryEnvelope, 
    DefenseIntentType, 
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

        # --- Governance-Specific: EXPORT_DEMOCRACY (Democracy only) ---
        # Private is CONQUEST, public is EXPORT_DEMOCRACY → moral washing (liberation framing)
        (DefenseIntentType.CONQUEST, DefenseIntentType.EXPORT_DEMOCRACY): 0.95,
        (DefenseIntentType.DEFENSE, DefenseIntentType.EXPORT_DEMOCRACY): 0.3,
        (DefenseIntentType.DETERRENCE, DefenseIntentType.EXPORT_DEMOCRACY): 0.4,
        (DefenseIntentType.IDLE, DefenseIntentType.EXPORT_DEMOCRACY): 0.7,
        (DefenseIntentType.EXPORT_DEMOCRACY, DefenseIntentType.EXPORT_DEMOCRACY): 0.0,
        (DefenseIntentType.EXPORT_DEMOCRACY, DefenseIntentType.CONQUEST): 0.1,
        (DefenseIntentType.EXPORT_DEMOCRACY, DefenseIntentType.DEFENSE): 0.2,
        (DefenseIntentType.EXPORT_DEMOCRACY, DefenseIntentType.DETERRENCE): 0.2,
        (DefenseIntentType.EXPORT_DEMOCRACY, DefenseIntentType.IDLE): 0.3,

        # --- Governance-Specific: HOLY_WAR (Theocracy only) ---
        # Private is CONQUEST, public is HOLY_WAR → moral washing (sacred duty framing)
        (DefenseIntentType.CONQUEST, DefenseIntentType.HOLY_WAR): 0.95,
        (DefenseIntentType.DEFENSE, DefenseIntentType.HOLY_WAR): 0.3,
        (DefenseIntentType.DETERRENCE, DefenseIntentType.HOLY_WAR): 0.4,
        (DefenseIntentType.IDLE, DefenseIntentType.HOLY_WAR): 0.7,
        (DefenseIntentType.HOLY_WAR, DefenseIntentType.HOLY_WAR): 0.0,
        (DefenseIntentType.HOLY_WAR, DefenseIntentType.CONQUEST): 0.1,
        (DefenseIntentType.HOLY_WAR, DefenseIntentType.DEFENSE): 0.2,
        (DefenseIntentType.HOLY_WAR, DefenseIntentType.DETERRENCE): 0.2,
        (DefenseIntentType.HOLY_WAR, DefenseIntentType.IDLE): 0.3,

        # Cross-governance (EXPORT_DEMOCRACY vs HOLY_WAR and vice versa)
        (DefenseIntentType.EXPORT_DEMOCRACY, DefenseIntentType.HOLY_WAR): 0.5,
        (DefenseIntentType.HOLY_WAR, DefenseIntentType.EXPORT_DEMOCRACY): 0.5,
    }
    
    # --- FOREIGN DOMAIN DECEPTION MATRIX ---
    FOREIGN_MATRIX = {
        # Private is COERCION (Bully)
        (ForeignIntentType.COERCION, ForeignIntentType.COERCION): 0.0,
        (ForeignIntentType.COERCION, ForeignIntentType.COOPERATION): 0.85, # Backstabbing
        (ForeignIntentType.COERCION, ForeignIntentType.APPEASEMENT): 0.6,  # Feigned Weakness
        (ForeignIntentType.COERCION, ForeignIntentType.IDLE): 0.4,
        
        # Private is COOPERATION (Genuine Ally)
        (ForeignIntentType.COOPERATION, ForeignIntentType.COOPERATION): 0.0,
        (ForeignIntentType.COOPERATION, ForeignIntentType.COERCION): 0.3, # Tough Love?
        (ForeignIntentType.COOPERATION, ForeignIntentType.APPEASEMENT): 0.1,
        (ForeignIntentType.COOPERATION, ForeignIntentType.IDLE): 0.1,
        
        # Private is APPEASEMENT (Submissive)
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.APPEASEMENT): 0.0,
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.COOPERATION): 0.1,
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.COERCION): 0.5, # Bluffing Strength
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.IDLE): 0.2,
        
        # Private is IDLE
        (ForeignIntentType.IDLE, ForeignIntentType.IDLE): 0.0,
        (ForeignIntentType.IDLE, ForeignIntentType.COOPERATION): 0.5, # False Promise (was 0.2)
        (ForeignIntentType.IDLE, ForeignIntentType.COERCION): 0.3,
        (ForeignIntentType.IDLE, ForeignIntentType.APPEASEMENT): 0.1,

        # --- Governance-Specific: EXPORT_DEMOCRACY (Democracy only) ---
        # Private is COERCION, public is EXPORT_DEMOCRACY → moral washing (freedom framing)
        (ForeignIntentType.COERCION, ForeignIntentType.EXPORT_DEMOCRACY): 0.90,
        (ForeignIntentType.COOPERATION, ForeignIntentType.EXPORT_DEMOCRACY): 0.1,
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.EXPORT_DEMOCRACY): 0.4,
        (ForeignIntentType.IDLE, ForeignIntentType.EXPORT_DEMOCRACY): 0.6,
        (ForeignIntentType.EXPORT_DEMOCRACY, ForeignIntentType.EXPORT_DEMOCRACY): 0.0,
        (ForeignIntentType.EXPORT_DEMOCRACY, ForeignIntentType.COOPERATION): 0.1,
        (ForeignIntentType.EXPORT_DEMOCRACY, ForeignIntentType.COERCION): 0.3,
        (ForeignIntentType.EXPORT_DEMOCRACY, ForeignIntentType.APPEASEMENT): 0.2,
        (ForeignIntentType.EXPORT_DEMOCRACY, ForeignIntentType.IDLE): 0.2,

        # --- Governance-Specific: DIVINE_MANDATE (Theocracy only) ---
        # Private is COERCION, public is DIVINE_MANDATE → moral washing (sacred duty framing)
        (ForeignIntentType.COERCION, ForeignIntentType.DIVINE_MANDATE): 0.90,
        (ForeignIntentType.COOPERATION, ForeignIntentType.DIVINE_MANDATE): 0.1,
        (ForeignIntentType.APPEASEMENT, ForeignIntentType.DIVINE_MANDATE): 0.4,
        (ForeignIntentType.IDLE, ForeignIntentType.DIVINE_MANDATE): 0.6,
        (ForeignIntentType.DIVINE_MANDATE, ForeignIntentType.DIVINE_MANDATE): 0.0,
        (ForeignIntentType.DIVINE_MANDATE, ForeignIntentType.COOPERATION): 0.1,
        (ForeignIntentType.DIVINE_MANDATE, ForeignIntentType.COERCION): 0.3,
        (ForeignIntentType.DIVINE_MANDATE, ForeignIntentType.APPEASEMENT): 0.2,
        (ForeignIntentType.DIVINE_MANDATE, ForeignIntentType.IDLE): 0.2,

        # Cross-governance
        (ForeignIntentType.EXPORT_DEMOCRACY, ForeignIntentType.DIVINE_MANDATE): 0.5,
        (ForeignIntentType.DIVINE_MANDATE, ForeignIntentType.EXPORT_DEMOCRACY): 0.5,
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
        
        Averages defense and foreign domain scores only.
        Economic domain is excluded: economic actions are directly observable
        and lack the narrative framing needed for moral washing measurement.
        
        Returns:
            float: 0.0 (honest) to 1.0 (maximum deception)
        """
        defense_score = cls.calculate_defense_deception(
            envelope.defense_private_intent,
            envelope.defense_public_intent
        )
        foreign_score = cls.calculate_foreign_deception(
            envelope.foreign_private_intent,
            envelope.foreign_public_intent
        )
        
        return (defense_score + foreign_score) / 2.0
    
    @classmethod
    def calculate_detailed_score(cls, envelope: CountryEnvelope) -> dict:
        """
        Calculate detailed deception breakdown by domain.
        
        Returns:
            dict with keys: defense, foreign, total
        """
        defense_score = cls.calculate_defense_deception(
            envelope.defense_private_intent,
            envelope.defense_public_intent
        )
        foreign_score = cls.calculate_foreign_deception(
            envelope.foreign_private_intent,
            envelope.foreign_public_intent
        )
        
        return {
            "defense": defense_score,
            "foreign": foreign_score,
            "total": (defense_score + foreign_score) / 2.0
        }
