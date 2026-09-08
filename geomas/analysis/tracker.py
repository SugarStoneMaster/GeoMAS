"""
Behavior Tracking.

Data structures and tracker for logging agent behavior (deception + coherence) across turns.
"""

from dataclasses import dataclass
from typing import Dict, List
from geomas.agents.schemas import (
    CountryEnvelope, 
    GlobalStrategy,
    DefenseIntentType, 
    ForeignIntentType
)
from geomas.analysis.deception import DeceptionAnalyzer
from geomas.analysis.coherence import CoherenceAnalyzer


@dataclass
class BehaviorRecord:
    """Record of a nation's behavior data for a single turn."""
    turn: int
    nation_id: str
    
    # Intents (defense and foreign only — economic intents removed, no moral washing signal)
    defense_public: DefenseIntentType
    defense_private: DefenseIntentType
    foreign_public: ForeignIntentType
    foreign_private: ForeignIntentType
    
    # Deception scores (defense + foreign only)
    defense_deception: float
    foreign_deception: float
    total_deception: float
    
    # Strategy context
    global_strategy: GlobalStrategy
    coherence_score: float = 0.0


class BehaviorTracker:
    """
    Tracks behavior (deception + coherence) history across turns for all nations.
    
    Usage:
        tracker = BehaviorTracker()
        tracker.log_turn(envelope)  # Call each turn
        history = tracker.get_nation_history("nation_1")
    """
    
    def __init__(self):
        # nation_id -> list of BehaviorRecords
        self._history: Dict[str, List[BehaviorRecord]] = {}
        # turn -> nation_id -> BehaviorRecord
        self._by_turn: Dict[int, Dict[str, BehaviorRecord]] = {}
    
    def log_turn(self, envelope: CountryEnvelope) -> BehaviorRecord:
        """
        Log behavior data for a turn from an envelope.
        
        Returns the created BehaviorRecord.
        """
        # Calculate deception scores (defense + foreign only)
        detailed = DeceptionAnalyzer.calculate_detailed_score(envelope)
        
        # Calculate coherence score (defense + foreign only)
        coherence = CoherenceAnalyzer.calculate_score(
            envelope.global_strategy,
            envelope.defense_private_intent,
            envelope.foreign_private_intent
        )
        
        record = BehaviorRecord(
            turn=envelope.turn,
            nation_id=envelope.sender_id,
            defense_public=envelope.defense_public_intent,
            defense_private=envelope.defense_private_intent,
            foreign_public=envelope.foreign_public_intent,
            foreign_private=envelope.foreign_private_intent,
            defense_deception=detailed["defense"],
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
    
    def get_nation_history(self, nation_id: str) -> List[BehaviorRecord]:
        """Get all behavior records for a nation."""
        return self._history.get(nation_id, [])
    
    def get_turn_summary(self, turn: int) -> Dict[str, BehaviorRecord]:
        """Get all behavior records for a specific turn."""
        return self._by_turn.get(turn, {})
    
    def get_nation_average(self, nation_id: str) -> Dict[str, float]:
        """Calculate average scores for a nation."""
        history = self.get_nation_history(nation_id)
        if not history:
            return {"defense": 0.0, "foreign": 0.0, "total": 0.0, "coherence": 0.0}
        
        n = len(history)
        return {
            "defense": sum(r.defense_deception for r in history) / n,
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
