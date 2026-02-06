"""
Context Manager.

Central manager for LLM agent memory and context generation.
Handles relationship tracking, event logging, action history, and pruning.
"""

from typing import Dict, List, Optional, Any
from geomas.schemas.world import WorldState
from geomas.agents.context.memory.schemas import RelationshipSummary, NotableEvent, MyAction, EventType


class ContextManager:
    """
    Manages memory and generates context for LLM agents.
    
    Features:
    - Tracks bilateral relationships with trust trends
    - Logs notable world events
    - Records each nation's past actions
    - Prunes old data to stay within token budget
    - Builds formatted context for each agent type
    """
    
    # Token budget limits
    MAX_EVENTS = 50
    MAX_ACTIONS_PER_DOMAIN = 10
    MAX_RELATIONSHIP_EVENTS = 3
    
    def __init__(self, max_user_tokens: int = 4200):
        """
        Initialize the ContextManager.
        
        Args:
            max_user_tokens: Maximum tokens for user prompt section
        """
        self.max_user_tokens = max_user_tokens
        
        # Memory stores (keyed by nation_id)
        # relationship_summaries[nation_id][other_nation_id] = RelationshipSummary
        self.relationship_summaries: Dict[str, Dict[str, RelationshipSummary]] = {}
        
        # Global events visible to all
        self.global_events: List[NotableEvent] = []
        
        # Per-nation actions: nation_actions[nation_id] = [MyAction, ...]
        self.nation_actions: Dict[str, List[MyAction]] = {}
        
        # Trust history for trend calculation
        self._trust_history: Dict[str, Dict[str, List[float]]] = {}
    
    def initialize_from_world(self, world: WorldState) -> None:
        """
        Initialize memory from current world state.
        
        Call this at simulation start to set up initial relationships.
        
        Args:
            world: Current world state
        """
        for nation_id, nation in world.nations.items():
            self.relationship_summaries[nation_id] = {}
            self.nation_actions[nation_id] = []
            self._trust_history[nation_id] = {}
            
            # Initialize relationships with all other nations
            for other_id, other_nation in world.nations.items():
                if other_id == nation_id:
                    continue
                
                # Get current relationship status
                rel_status = "PEACE"
                if nation_id in world.relationship_matrix:
                    rel_status = world.relationship_matrix[nation_id].get(other_id, "PEACE")
                
                # Get current trust
                trust = 50.0
                if nation_id in world.trust_matrix:
                    trust = world.trust_matrix[nation_id].get(other_id, 50.0)
                
                self.relationship_summaries[nation_id][other_id] = RelationshipSummary(
                    other_nation_id=other_id,
                    other_nation_name=other_nation.name,
                    relationship=rel_status,
                    trust=trust,
                    trust_trend="→",
                )
                
                self._trust_history[nation_id][other_id] = [trust]
    
    def update_after_turn(
        self,
        turn: int,
        envelopes: List[Any],  # List[CountryEnvelope]
        world: WorldState
    ) -> None:
        """
        Update all memory stores after a turn completes.
        
        Args:
            turn: Current turn number
            envelopes: Actions executed this turn
            world: Updated world state
        """
        self._update_relationships(world)
        self._extract_events(turn, envelopes, world)
        self._log_actions(turn, envelopes)
        self._prune_if_needed()
    
    def _update_relationships(self, world: WorldState) -> None:
        """Update relationship summaries from world state."""
        for nation_id in world.nations.keys():
            if nation_id not in self.relationship_summaries:
                continue
            
            for other_id in world.nations.keys():
                if other_id == nation_id:
                    continue
                
                if other_id not in self.relationship_summaries[nation_id]:
                    continue
                
                summary = self.relationship_summaries[nation_id][other_id]
                
                # Update relationship status
                if nation_id in world.relationship_matrix:
                    summary.relationship = world.relationship_matrix[nation_id].get(
                        other_id, "PEACE"
                    )
                
                # Update trust and calculate trend
                if nation_id in world.trust_matrix:
                    new_trust = world.trust_matrix[nation_id].get(other_id, 50.0)
                    
                    # Track history for trend
                    history = self._trust_history[nation_id].get(other_id, [])
                    history.append(new_trust)
                    
                    # Keep last 5 values for trend
                    if len(history) > 5:
                        history = history[-5:]
                    self._trust_history[nation_id][other_id] = history
                    
                    # Calculate trend
                    if len(history) >= 2:
                        delta = history[-1] - history[0]
                        if delta > 5:
                            summary.trust_trend = "↑"
                        elif delta < -5:
                            summary.trust_trend = "↓"
                        else:
                            summary.trust_trend = "→"
                    
                    summary.trust = new_trust
    
    def _extract_events(
        self, 
        turn: int, 
        envelopes: List[Any],
        world: WorldState
    ) -> None:
        """Extract notable events from turn envelopes."""
        for envelope in envelopes:
            nation_id = envelope.sender_id
            
            # Extract events from payloads
            for payload in [envelope.defense_payload, envelope.economic_payload, envelope.foreign_payload]:
                if payload is None:
                    continue
                for action in getattr(payload, 'actions', []):
                    event = self._behavior_to_event(turn, nation_id, action, world)
                    if event:
                        self.global_events.append(event)
                        self._add_event_to_relationships(turn, nation_id, event)
    
    def _behavior_to_event(
        self, 
        turn: int, 
        nation_id: str, 
        behavior: Any,
        world: WorldState
    ) -> Optional[NotableEvent]:
        """Convert a behavior to a notable event if significant."""
        action_type = behavior.action_type if hasattr(behavior, 'action_type') else str(type(behavior).__name__)
        
        nation_name = world.nations[nation_id].name if nation_id in world.nations else nation_id
        
        # War declaration
        if "DECLARE_WAR" in action_type:
            target_id = getattr(behavior, 'target_nation_id', None)
            target_name = world.nations[target_id].name if target_id and target_id in world.nations else target_id
            return NotableEvent(
                turn=turn,
                event_type=EventType.WAR_DECLARED,
                actors=[nation_id, target_id] if target_id else [nation_id],
                summary=f"{nation_name} declared war on {target_name}",
                relevance_to=None  # Global event
            )
        
        # Peace treaty
        if "PEACE" in action_type and "ACCEPT" in action_type:
            other_id = getattr(behavior, 'from_nation_id', None)
            other_name = world.nations[other_id].name if other_id and other_id in world.nations else other_id
            return NotableEvent(
                turn=turn,
                event_type=EventType.PEACE_SIGNED,
                actors=[nation_id, other_id] if other_id else [nation_id],
                summary=f"{nation_name} and {other_name} signed peace treaty",
                relevance_to=None
            )
        
        # Alliance formed
        if "ALLIANCE" in action_type and "ACCEPT" in action_type:
            other_id = getattr(behavior, 'from_nation_id', None)
            other_name = world.nations[other_id].name if other_id and other_id in world.nations else other_id
            return NotableEvent(
                turn=turn,
                event_type=EventType.ALLIANCE_FORMED,
                actors=[nation_id, other_id] if other_id else [nation_id],
                summary=f"{nation_name} and {other_name} formed alliance",
                relevance_to=None
            )
        
        # Attack
        if "ATTACK" in action_type:
            target_id = getattr(behavior, 'target_province_id', None)
            target_nation = None
            if target_id and target_id in world.provinces:
                target_nation = world.provinces[target_id].owner_id
            target_name = world.nations[target_nation].name if target_nation and target_nation in world.nations else "unknown"
            
            outcome = getattr(behavior, 'outcome', None)
            if outcome == "CAPTURED":
                return NotableEvent(
                    turn=turn,
                    event_type=EventType.TERRITORY_GAINED,
                    actors=[nation_id, target_nation] if target_nation else [nation_id],
                    summary=f"{nation_name} captured territory from {target_name}",
                    relevance_to=target_nation
                )
        
        # Trade deal
        if "TRADE" in action_type and "ACCEPT" in action_type:
            other_id = getattr(behavior, 'from_nation_id', None)
            other_name = world.nations[other_id].name if other_id and other_id in world.nations else other_id
            return NotableEvent(
                turn=turn,
                event_type=EventType.TRADE_DEAL,
                actors=[nation_id, other_id] if other_id else [nation_id],
                summary=f"{nation_name} signed trade deal with {other_name}",
                relevance_to=None
            )
        
        return None
    
    def _add_event_to_relationships(
        self, 
        turn: int, 
        nation_id: str, 
        event: NotableEvent
    ) -> None:
        """Add event to relevant relationship summaries."""
        for actor_id in event.actors:
            if actor_id == nation_id or actor_id is None:
                continue
            
            if nation_id in self.relationship_summaries:
                if actor_id in self.relationship_summaries[nation_id]:
                    summary = self.relationship_summaries[nation_id][actor_id]
                    summary.notable_events.append(f"T{turn}: {event.summary}")
                    summary.last_interaction_turn = turn
                    summary.last_interaction_summary = event.summary[:50]  # Truncate
                    
                    # Limit notable events
                    if len(summary.notable_events) > self.MAX_RELATIONSHIP_EVENTS:
                        summary.notable_events = summary.notable_events[-self.MAX_RELATIONSHIP_EVENTS:]
    
    def _log_actions(self, turn: int, envelopes: List[Any]) -> None:
        """Log actions from envelopes to nation action history."""
        for envelope in envelopes:
            nation_id = envelope.sender_id
            
            if nation_id not in self.nation_actions:
                self.nation_actions[nation_id] = []
            
            # Extract actions from payloads
            for payload in [envelope.defense_payload, envelope.economic_payload, envelope.foreign_payload]:
                if payload is None:
                    continue
                for action_item in getattr(payload, 'actions', []):
                    action = self._behavior_to_action(turn, action_item)
                    if action:
                        self.nation_actions[nation_id].append(action)
    
    def _behavior_to_action(self, turn: int, behavior: Any) -> Optional[MyAction]:
        """Convert behavior to MyAction record."""
        action_type = behavior.action_type if hasattr(behavior, 'action_type') else str(type(behavior).__name__)
        
        # Determine domain
        if any(x in action_type for x in ["ATTACK", "MOVE", "CREATE_UNIT", "FORTIFY"]):
            domain = "Defense"
        elif any(x in action_type for x in ["TRADE", "WELFARE", "TAX", "INVEST"]):
            domain = "Economy"
        elif any(x in action_type for x in ["ALLIANCE", "WAR", "PEACE", "MESSAGE"]):
            domain = "Foreign"
        else:
            domain = "Other"
        
        # Get summary and outcome
        summary = getattr(behavior, 'description', action_type)
        outcome = getattr(behavior, 'outcome', None)
        
        return MyAction(
            turn=turn,
            domain=domain,
            action_type=action_type,
            action_summary=summary[:60] if len(summary) > 60 else summary,
            outcome=outcome
        )
    
    def _prune_if_needed(self) -> None:
        """Prune old events and actions to stay within budget."""
        # Prune global events
        if len(self.global_events) > self.MAX_EVENTS:
            # Keep critical events + most recent
            critical = [e for e in self.global_events if e.is_critical()]
            recent = [e for e in self.global_events if not e.is_critical()]
            recent = recent[-(self.MAX_EVENTS - len(critical)):]
            self.global_events = sorted(critical + recent, key=lambda e: e.turn)
        
        # Prune per-nation actions
        for nation_id in self.nation_actions:
            actions = self.nation_actions[nation_id]
            
            # Group by domain and keep last N per domain
            by_domain: Dict[str, List[MyAction]] = {}
            for action in actions:
                if action.domain not in by_domain:
                    by_domain[action.domain] = []
                by_domain[action.domain].append(action)
            
            # Prune each domain
            pruned = []
            for domain, domain_actions in by_domain.items():
                pruned.extend(domain_actions[-self.MAX_ACTIONS_PER_DOMAIN:])
            
            self.nation_actions[nation_id] = sorted(pruned, key=lambda a: a.turn)
    
    def get_relationships_for(self, nation_id: str) -> List[str]:
        """
        Get formatted relationship lines for a nation.
        
        Args:
            nation_id: Nation to get relationships for
            
        Returns:
            List of formatted relationship strings
        """
        if nation_id not in self.relationship_summaries:
            return []
        
        lines = []
        for summary in self.relationship_summaries[nation_id].values():
            lines.append(summary.to_prompt_line())
        
        return lines
    
    def get_events_for(self, nation_id: str, max_events: int = 15) -> List[str]:
        """
        Get formatted event lines relevant to a nation.
        
        Args:
            nation_id: Nation to get events for
            max_events: Maximum events to return
            
        Returns:
            List of formatted event strings
        """
        relevant = []
        
        for event in self.global_events:
            # Include if: global, or involves this nation, or relevant to this nation
            if (event.relevance_to is None or 
                event.relevance_to == nation_id or
                nation_id in event.actors):
                relevant.append(event)
        
        # Sort by turn descending, take most recent
        relevant = sorted(relevant, key=lambda e: e.turn, reverse=True)[:max_events]
        relevant = sorted(relevant, key=lambda e: e.turn)  # Re-sort chronologically
        
        return [e.to_prompt_line() for e in relevant]
    
    def get_actions_for(self, nation_id: str, domain: Optional[str] = None, max_actions: int = 10) -> List[str]:
        """
        Get formatted action lines for a nation.
        
        Args:
            nation_id: Nation to get actions for
            domain: Optional domain filter ("Defense", "Economy", "Foreign")
            max_actions: Maximum actions to return
            
        Returns:
            List of formatted action strings
        """
        if nation_id not in self.nation_actions:
            return []
        
        actions = self.nation_actions[nation_id]
        
        if domain:
            actions = [a for a in actions if a.domain == domain]
        
        # Most recent
        actions = actions[-max_actions:]
        
        return [a.to_prompt_line() for a in actions]
