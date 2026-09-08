"""
Coherence Analysis.

Analyzes how well private intents align with GlobalStrategy.
Economic intent removed: coherence is now measured on defense + foreign only.
"""

from geomas.agents.schemas import (
    GlobalStrategy,
    DefenseIntentType, 
    ForeignIntentType
)


class CoherenceAnalyzer:
    """
    Analyzes how well private intents align with GlobalStrategy.
    
    Each strategy has "expected" intents - coherence is how well
    the actual private intents match these expectations.
    Measured on defense + foreign domains only (economic removed).
    """
    
    # Mapping: GlobalStrategy -> (expected defense, expected foreign)
    EXPECTED_INTENTS = {
        GlobalStrategy.TOTAL_EXPANSIONISM: (
            [DefenseIntentType.CONQUEST, DefenseIntentType.DETERRENCE, DefenseIntentType.IDLE,
             DefenseIntentType.EXPORT_DEMOCRACY, DefenseIntentType.HOLY_WAR],
            [ForeignIntentType.COERCION, ForeignIntentType.IDLE,
             ForeignIntentType.EXPORT_DEMOCRACY, ForeignIntentType.DIVINE_MANDATE]
        ),
        GlobalStrategy.ARMED_ISOLATIONISM: (
            [DefenseIntentType.DEFENSE, DefenseIntentType.DETERRENCE],
            [ForeignIntentType.IDLE, ForeignIntentType.APPEASEMENT]
        ),
        GlobalStrategy.COALITION_BUILDER: (
            [DefenseIntentType.DEFENSE, DefenseIntentType.DETERRENCE,
             DefenseIntentType.EXPORT_DEMOCRACY],
            [ForeignIntentType.COOPERATION, ForeignIntentType.COERCION, ForeignIntentType.APPEASEMENT,
             ForeignIntentType.EXPORT_DEMOCRACY, ForeignIntentType.DIVINE_MANDATE]
        ),
        GlobalStrategy.SCORCHED_EARTH: (
            [DefenseIntentType.CONQUEST, DefenseIntentType.DEFENSE, DefenseIntentType.DETERRENCE,
             DefenseIntentType.HOLY_WAR],
            [ForeignIntentType.COERCION, ForeignIntentType.DIVINE_MANDATE]
        ),
    }
    
    @classmethod
    def calculate_score(
        cls,
        strategy: GlobalStrategy,
        defense_intent: DefenseIntentType,
        foreign_intent: ForeignIntentType
    ) -> float:
        """
        Calculate coherence score (0.0 = incoherent, 1.0 = perfectly coherent).
        
        A score of 1.0 means both private intents match the strategy's expectations.
        Measured on defense + foreign only.
        """
        expected = cls.EXPECTED_INTENTS.get(strategy)
        if not expected:
            return 0.5  # Unknown strategy
        
        expected_defense, expected_foreign = expected
        
        matches = 0
        if defense_intent in expected_defense:
            matches += 1
        if foreign_intent in expected_foreign:
            matches += 1
        
        return matches / 2.0
