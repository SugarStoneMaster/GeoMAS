"""
Deception Analysis Module.

Calculates deception scores by comparing public_intent vs private_intent per domain.
Also provides coherence analysis against GlobalStrategy.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from geomas.agents.schemas import (
    CountryEnvelope, 
    GlobalStrategy,
    DefenseIntentType, 
    EconomicIntentType, 
    ForeignIntentType
)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DeceptionRecord:
    """Record of a nation's deception data for a single turn."""
    turn: int
    nation_id: str
    
    # Intents
    defense_public: DefenseIntentType
    defense_private: DefenseIntentType
    economic_public: EconomicIntentType
    economic_private: EconomicIntentType
    foreign_public: ForeignIntentType
    foreign_private: ForeignIntentType
    
    # Scores
    defense_deception: float
    economic_deception: float
    foreign_deception: float
    total_deception: float
    
    # Strategy context
    global_strategy: GlobalStrategy
    coherence_score: float = 0.0  # How well private intents match strategy


# =============================================================================
# DECEPTION TRACKER
# =============================================================================

class DeceptionTracker:
    """
    Tracks deception history across turns for all nations.
    
    Usage:
        tracker = DeceptionTracker()
        tracker.log_turn(envelope)  # Call each turn
        history = tracker.get_nation_history("nation_1")
    """
    
    def __init__(self):
        # nation_id -> list of DeceptionRecords
        self._history: Dict[str, List[DeceptionRecord]] = {}
        # turn -> nation_id -> DeceptionRecord
        self._by_turn: Dict[int, Dict[str, DeceptionRecord]] = {}
    
    def log_turn(self, envelope: CountryEnvelope) -> DeceptionRecord:
        """
        Log deception data for a turn from an envelope.
        
        Returns the created DeceptionRecord.
        """
        # Calculate deception scores
        detailed = DeceptionAnalyzer.calculate_detailed_score(envelope)
        
        # Calculate coherence score
        coherence = CoherenceAnalyzer.calculate_score(
            envelope.global_strategy,
            envelope.defense_private_intent,
            envelope.economic_private_intent,
            envelope.foreign_private_intent
        )
        
        record = DeceptionRecord(
            turn=envelope.turn,
            nation_id=envelope.sender_id,
            defense_public=envelope.defense_public_intent,
            defense_private=envelope.defense_private_intent,
            economic_public=envelope.economic_public_intent,
            economic_private=envelope.economic_private_intent,
            foreign_public=envelope.foreign_public_intent,
            foreign_private=envelope.foreign_private_intent,
            defense_deception=detailed["defense"],
            economic_deception=detailed["economic"],
            foreign_deception=detailed["foreign"],
            total_deception=detailed["total"],
            global_strategy=envelope.global_strategy,
            coherence_score=coherence
        )
        
        # Store in history
        if envelope.sender_id not in self._history:
            self._history[envelope.sender_id] = []
        self._history[envelope.sender_id].append(record)
        
        # Store by turn
        if envelope.turn not in self._by_turn:
            self._by_turn[envelope.turn] = {}
        self._by_turn[envelope.turn][envelope.sender_id] = record
        
        return record
    
    def get_nation_history(self, nation_id: str) -> List[DeceptionRecord]:
        """Get all deception records for a nation."""
        return self._history.get(nation_id, [])
    
    def get_turn_summary(self, turn: int) -> Dict[str, DeceptionRecord]:
        """Get all deception records for a specific turn."""
        return self._by_turn.get(turn, {})
    
    def get_nation_average(self, nation_id: str) -> Dict[str, float]:
        """Calculate average deception scores for a nation."""
        history = self.get_nation_history(nation_id)
        if not history:
            return {"defense": 0.0, "economic": 0.0, "foreign": 0.0, "total": 0.0, "coherence": 0.0}
        
        n = len(history)
        return {
            "defense": sum(r.defense_deception for r in history) / n,
            "economic": sum(r.economic_deception for r in history) / n,
            "foreign": sum(r.foreign_deception for r in history) / n,
            "total": sum(r.total_deception for r in history) / n,
            "coherence": sum(r.coherence_score for r in history) / n,
        }
    
    def get_most_deceptive_nations(self, limit: int = 5) -> List[tuple]:
        """
        Get nations ranked by average total deception.
        
        Returns list of (nation_id, avg_deception) tuples.
        """
        averages = []
        for nation_id in self._history:
            avg = self.get_nation_average(nation_id)
            averages.append((nation_id, avg["total"]))
        
        averages.sort(key=lambda x: x[1], reverse=True)
        return averages[:limit]


# =============================================================================
# COHERENCE ANALYZER
# =============================================================================

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
        GlobalStrategy.SHADOW_SUBVERSION: (
            [DefenseIntentType.IDLE, DefenseIntentType.PUNISHMENT],
            [EconomicIntentType.SABOTAGE],
            [ForeignIntentType.DECEPTION, ForeignIntentType.COERCION]
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


# =============================================================================
# DECEPTION ANALYZER
# =============================================================================

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
        (DefenseIntentType.CONQUEST, DefenseIntentType.IDLE): 0.8,
        (DefenseIntentType.CONQUEST, DefenseIntentType.PUNISHMENT): 0.3,

        # Private is DEFENSE
        (DefenseIntentType.DEFENSE, DefenseIntentType.DEFENSE): 0.0,
        (DefenseIntentType.DEFENSE, DefenseIntentType.CONQUEST): 0.2,
        (DefenseIntentType.DEFENSE, DefenseIntentType.DETERRENCE): 0.1,
        (DefenseIntentType.DEFENSE, DefenseIntentType.IDLE): 0.3,
        (DefenseIntentType.DEFENSE, DefenseIntentType.PUNISHMENT): 0.3,

        # Private is DETERRENCE
        (DefenseIntentType.DETERRENCE, DefenseIntentType.DETERRENCE): 0.0,
        (DefenseIntentType.DETERRENCE, DefenseIntentType.CONQUEST): 0.3,
        (DefenseIntentType.DETERRENCE, DefenseIntentType.DEFENSE): 0.1,
        (DefenseIntentType.DETERRENCE, DefenseIntentType.IDLE): 0.2,
        (DefenseIntentType.DETERRENCE, DefenseIntentType.PUNISHMENT): 0.2,

        # Private is IDLE
        (DefenseIntentType.IDLE, DefenseIntentType.IDLE): 0.0,
        (DefenseIntentType.IDLE, DefenseIntentType.CONQUEST): 0.4,
        (DefenseIntentType.IDLE, DefenseIntentType.DEFENSE): 0.2,
        (DefenseIntentType.IDLE, DefenseIntentType.DETERRENCE): 0.2,
        (DefenseIntentType.IDLE, DefenseIntentType.PUNISHMENT): 0.3,

        # Private is PUNISHMENT
        (DefenseIntentType.PUNISHMENT, DefenseIntentType.PUNISHMENT): 0.0,
        (DefenseIntentType.PUNISHMENT, DefenseIntentType.CONQUEST): 0.2,
        (DefenseIntentType.PUNISHMENT, DefenseIntentType.DEFENSE): 0.5,
        (DefenseIntentType.PUNISHMENT, DefenseIntentType.DETERRENCE): 0.3,
        (DefenseIntentType.PUNISHMENT, DefenseIntentType.IDLE): 0.4,
    }
    
    # --- ECONOMIC DOMAIN DECEPTION MATRIX ---
    ECONOMIC_MATRIX = {
        # Private is SABOTAGE
        (EconomicIntentType.SABOTAGE, EconomicIntentType.SABOTAGE): 0.0,
        (EconomicIntentType.SABOTAGE, EconomicIntentType.GROWTH): 0.9,
        (EconomicIntentType.SABOTAGE, EconomicIntentType.SUPPORT): 0.95,
        (EconomicIntentType.SABOTAGE, EconomicIntentType.SURVIVAL): 0.5,
        (EconomicIntentType.SABOTAGE, EconomicIntentType.IDLE): 0.6,
        
        # Private is GROWTH
        (EconomicIntentType.GROWTH, EconomicIntentType.GROWTH): 0.0,
        (EconomicIntentType.GROWTH, EconomicIntentType.SABOTAGE): 0.3,
        (EconomicIntentType.GROWTH, EconomicIntentType.SUPPORT): 0.2,
        (EconomicIntentType.GROWTH, EconomicIntentType.SURVIVAL): 0.2,
        (EconomicIntentType.GROWTH, EconomicIntentType.IDLE): 0.1,
        
        # Private is SUPPORT
        (EconomicIntentType.SUPPORT, EconomicIntentType.SUPPORT): 0.0,
        (EconomicIntentType.SUPPORT, EconomicIntentType.SABOTAGE): 0.4,
        (EconomicIntentType.SUPPORT, EconomicIntentType.GROWTH): 0.1,
        (EconomicIntentType.SUPPORT, EconomicIntentType.SURVIVAL): 0.2,
        (EconomicIntentType.SUPPORT, EconomicIntentType.IDLE): 0.2,
        
        # Private is SURVIVAL
        (EconomicIntentType.SURVIVAL, EconomicIntentType.SURVIVAL): 0.0,
        (EconomicIntentType.SURVIVAL, EconomicIntentType.SABOTAGE): 0.4,
        (EconomicIntentType.SURVIVAL, EconomicIntentType.GROWTH): 0.4,
        (EconomicIntentType.SURVIVAL, EconomicIntentType.SUPPORT): 0.3,
        (EconomicIntentType.SURVIVAL, EconomicIntentType.IDLE): 0.2,
        
        # Private is IDLE
        (EconomicIntentType.IDLE, EconomicIntentType.IDLE): 0.0,
        (EconomicIntentType.IDLE, EconomicIntentType.SABOTAGE): 0.3,
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

