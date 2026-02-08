"""
Coherence Analysis.

Analyzes how well private intents align with GlobalStrategy.
"""

from geomas.agents.schemas import (
    GlobalStrategy,
    DefenseIntentType, 
    EconomicIntentType, 
    ForeignIntentType
)


class CoherenceAnalyzer:
    """
    Analyzes how well private intents align with GlobalStrategy.
    
    Each strategy has "expected" intents - coherence is how well
    the actual private intents match these expectations.
    """
    
    # Mapping: GlobalStrategy -> (expected defense, expected economic, expected foreign)
    EXPECTED_INTENTS = {
        GlobalStrategy.TOTAL_EXPANSIONISM: (
            [DefenseIntentType.CONQUEST],
            [EconomicIntentType.GROWTH, EconomicIntentType.SABOTAGE],
            [ForeignIntentType.COERCION, ForeignIntentType.DECEPTION]
        ),
        GlobalStrategy.ARMED_ISOLATIONISM: (
            [DefenseIntentType.DEFENSE, DefenseIntentType.DETERRENCE],
            [EconomicIntentType.GROWTH, EconomicIntentType.SURVIVAL],
            [ForeignIntentType.IDLE, ForeignIntentType.APPEASEMENT]
        ),
        GlobalStrategy.MERCANTILE_HEGEMONY: (
            [DefenseIntentType.DETERRENCE, DefenseIntentType.IDLE],
            [EconomicIntentType.GROWTH, EconomicIntentType.SUPPORT],
            [ForeignIntentType.COOPERATION, ForeignIntentType.COERCION]
        ),
        GlobalStrategy.DOMESTIC_RECOVERY: (
            [DefenseIntentType.DEFENSE, DefenseIntentType.IDLE],
            [EconomicIntentType.SURVIVAL, EconomicIntentType.GROWTH],
            [ForeignIntentType.APPEASEMENT, ForeignIntentType.IDLE]
        ),
        GlobalStrategy.COALITION_BUILDER: (
            [DefenseIntentType.DEFENSE, DefenseIntentType.DETERRENCE],
            [EconomicIntentType.SUPPORT, EconomicIntentType.GROWTH],
            [ForeignIntentType.COOPERATION]
        ),
        GlobalStrategy.SCORCHED_EARTH: (
            [DefenseIntentType.CONQUEST, DefenseIntentType.PUNISHMENT],
            [EconomicIntentType.SABOTAGE, EconomicIntentType.SURVIVAL],
            [ForeignIntentType.COERCION, ForeignIntentType.DECEPTION]
        ),
    }
    
    @classmethod
    def calculate_score(
        cls,
        strategy: GlobalStrategy,
        defense_intent: DefenseIntentType,
        economic_intent: EconomicIntentType,
        foreign_intent: ForeignIntentType
    ) -> float:
        """
        Calculate coherence score (0.0 = incoherent, 1.0 = perfectly coherent).
        
        A score of 1.0 means all private intents match the strategy's expectations.
        """
        expected = cls.EXPECTED_INTENTS.get(strategy)
        if not expected:
            return 0.5  # Unknown strategy
        
        expected_defense, expected_economic, expected_foreign = expected
        
        matches = 0
        if defense_intent in expected_defense:
            matches += 1
        if economic_intent in expected_economic:
            matches += 1
        if foreign_intent in expected_foreign:
            matches += 1
        
        return matches / 3.0
