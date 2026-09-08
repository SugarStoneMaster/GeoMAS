"""
In-Memory Turn Cache.

Caches recent turns to avoid DB queries during simulation.
Provides fast access to world snapshots, envelopes, and behaviors.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
from copy import deepcopy

from geomas.schemas.world import WorldState
from geomas.agents.schemas import CountryEnvelope


@dataclass
class TurnSnapshot:
    """Complete snapshot of a single turn's data."""
    turn: int
    world_state: WorldState
    envelopes: List[CountryEnvelope] = field(default_factory=list)
    behaviors: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # behaviors[nation_id] = {deception_total, deception_defense, ..., coherence_score}


class TurnCache:
    """
    In-events cache for recent simulation turns.
    
    Provides O(1) access to last N turns without DB queries.
    Used during simulation for quick context retrieval.
    
    Usage:
        cache = TurnCache(max_turns=20)
        
        # After each turn
        cache.add_turn(turn, world, envelopes, behaviors)
        
        # Query
        snapshot = cache.get_turn(5)
        recent = cache.get_recent_turns(10)
        envelopes = cache.get_envelopes_for_nation("nation_1")
    """
    
    def __init__(self, max_turns: int = 20):
        """
        Initialize cache with maximum turn capacity.
        
        Args:
            max_turns: Maximum number of turns to keep in cache.
                      Older turns are automatically evicted.
        """
        self.max_turns = max_turns
        self._turns: deque[TurnSnapshot] = deque(maxlen=max_turns)
        self._turn_index: Dict[int, TurnSnapshot] = {}
    
    def add_turn(
        self,
        turn: int,
        world_state: WorldState,
        envelopes: List[CountryEnvelope],
        behaviors: Optional[Dict[str, Dict[str, float]]] = None
    ) -> None:
        """
        Add a turn to the cache.
        
        Args:
            turn: Turn number
            world_state: WorldState at end of turn
            envelopes: All CountryEnvelopes for this turn
            behaviors: Optional behavior metrics per nation
        """
        snapshot = TurnSnapshot(
            turn=turn,
            world_state=deepcopy(world_state),
            envelopes=list(envelopes),
            behaviors=behaviors or {}
        )
        
        # Remove from index if at capacity and oldest will be evicted
        if len(self._turns) == self.max_turns:
            oldest = self._turns[0]
            self._turn_index.pop(oldest.turn, None)
        
        self._turns.append(snapshot)
        self._turn_index[turn] = snapshot
    
    def update_turn_envelopes(
        self, 
        turn: int, 
        envelopes: List[CountryEnvelope],
        behaviors: Optional[Dict[str, Dict[str, float]]] = None
    ) -> None:
        """
        Update existing turn snapshot with envelopes and behaviors.
        Used when simulation splits execution and state persistence.
        """
        snapshot = self.get_turn(turn)
        if snapshot:
            snapshot.envelopes = list(envelopes)
            if behaviors:
                snapshot.behaviors = behaviors
    
    def get_turn(self, turn: int) -> Optional[TurnSnapshot]:
        """
        Get snapshot for a specific turn.
        
        Returns:
            TurnSnapshot or None if turn not in cache
        """
        return self._turn_index.get(turn)
    
    def get_world_at_turn(self, turn: int) -> Optional[WorldState]:
        """
        Get WorldState for a specific turn.
        
        Returns:
            WorldState or None if turn not in cache
        """
        snapshot = self.get_turn(turn)
        return snapshot.world_state if snapshot else None
    
    def get_recent_turns(self, n: int = 10) -> List[TurnSnapshot]:
        """
        Get the N most recent turns.
        
        Args:
            n: Number of recent turns to retrieve
            
        Returns:
            List of TurnSnapshots, newest first
        """
        return list(reversed(list(self._turns)))[:n]
    
    def get_envelopes_at_turn(self, turn: int) -> List[CountryEnvelope]:
        """
        Get all envelopes for a specific turn.
        
        Returns:
            List of CountryEnvelopes or empty list if turn not found
        """
        snapshot = self.get_turn(turn)
        return snapshot.envelopes if snapshot else []
    
    def get_envelopes_for_nation(
        self, 
        nation_id: str, 
        n_turns: Optional[int] = None
    ) -> List[CountryEnvelope]:
        """
        Get all envelopes for a nation across cached turns.
        
        Args:
            nation_id: Nation identifier
            n_turns: Optional limit on number of recent turns
            
        Returns:
            List of CountryEnvelopes, newest first
        """
        result = []
        turns = self.get_recent_turns(n_turns or self.max_turns)
        
        for snapshot in turns:
            for envelope in snapshot.envelopes:
                if envelope.sender_id == nation_id:
                    result.append(envelope)
        
        return result
    
    def get_behaviors_for_nation(
        self, 
        nation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get behavior history for a nation.
        
        Returns:
            List of behavior dicts with turn number, newest first
        """
        result = []
        for snapshot in reversed(self._turns):
            if nation_id in snapshot.behaviors:
                behavior = snapshot.behaviors[nation_id].copy()
                behavior['turn'] = snapshot.turn
                result.append(behavior)
        return result
    
    @property
    def current_turn(self) -> int:
        """Get the most recent turn number in cache."""
        if not self._turns:
            return 0
        return self._turns[-1].turn
    
    @property
    def oldest_turn(self) -> int:
        """Get the oldest turn number in cache."""
        if not self._turns:
            return 0
        return self._turns[0].turn
    
    def __len__(self) -> int:
        """Number of turns in cache."""
        return len(self._turns)
    
    def __contains__(self, turn: int) -> bool:
        """Check if a turn is in cache."""
        return turn in self._turn_index
    
    def clear(self) -> None:
        """Clear all cached turns."""
        self._turns.clear()
        self._turn_index.clear()
