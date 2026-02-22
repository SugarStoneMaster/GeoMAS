"""
Context Manager.

Central manager for LLM agent events and context generation.
Handles relationship tracking, event logging, action history, and pruning.
"""

from typing import Dict, List, Optional, Any
from geomas.schemas.world import WorldState
from geomas.agents.context.events.schemas import RelationshipSummary, NotableEvent, MyAction, EventType


class ContextManager:
    """
    Manages events and generates context for LLM agents.
    
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
    MAX_ACTIONS_PRESIDENT = 15
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

    def get_state(self) -> Dict[str, Any]:
        """Get full internal state for serialization."""
        return {
            "relationship_summaries": self.relationship_summaries,
            "global_events": self.global_events,
            "nation_actions": self.nation_actions,
            "trust_history": self._trust_history
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """Load internal state from dictionary."""
        self.relationship_summaries = state.get("relationship_summaries", {})
        self.global_events = state.get("global_events", [])
        self.nation_actions = state.get("nation_actions", {})
        self._trust_history = state.get("trust_history", {})
    
    def initialize_from_world(self, world: WorldState) -> None:
        """
        Initialize events from current world state.
        
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

        # Load structured Genesis events if present
        self.global_events = []
        for event_data in world.global_events:
            # Check if it's already a NotableEvent (backwards compatibility)
            if isinstance(event_data, NotableEvent):
                self.global_events.append(event_data)
                continue
                
            # Parse dict from Genesis
            if isinstance(event_data, dict):
                try:
                    event = NotableEvent(
                        turn=event_data.get("turn", 0),
                        event_type=event_data.get("event_type", EventType.DIPLOMATIC_MESSAGE.value),
                        actors=event_data.get("actors", []),
                        summary=event_data.get("summary", "")
                    )
                    self.global_events.append(event)
                except Exception as e:
                    print(f"Failed to parse Genesis event: {e}")
                    
        # Backward compatibility: if global_events still contains strings from old saves
        for e in world.global_events:
            if isinstance(e, str):
                 self.global_events.append(NotableEvent(
                     turn=0, 
                     event_type=EventType.DIPLOMATIC_MESSAGE,
                     actors=[],
                     summary=e
                 ))
    
    def update_after_turn(
        self,
        turn: int,
        envelopes: List[Any],  # List[CountryEnvelope]
        world: WorldState
    ) -> None:
        """
        Update all events stores after a turn completes.
        
        Args:
            turn: Current turn number
            envelopes: Actions executed this turn
            world: Updated world state
        """
        self._update_relationships(world)
        self._extract_events(turn, envelopes, world)
        self._log_actions(turn, envelopes)
        self._log_presidential_decisions(turn, envelopes)
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
            
            # Defense: Multiple moves
            if envelope.defense_payload:
                for move in envelope.defense_payload.moves:
                    event = self._behavior_to_event(turn, nation_id, move, world)
                    if event:
                        self.global_events.append(event)
                        self._add_event_to_relationships(turn, nation_id, event)
            
            # Economy: Single action
            if envelope.economic_payload and envelope.economic_payload.action_type:
                event = self._behavior_to_event(turn, nation_id, envelope.economic_payload, world)
                if event:
                    self.global_events.append(event)
                    self._add_event_to_relationships(turn, nation_id, event)
            
            # Foreign: Responses and Single action
            if envelope.foreign_payload:
                # 1. Process explicit responses (if any)
                outcome = getattr(envelope.foreign_payload, "execution_outcome", None)
                if outcome and outcome.details and "responses" in outcome.details:
                    for resp in outcome.details["responses"]:
                        if resp.get("success") and resp.get("event_type"):
                             event = self._response_detail_to_event(turn, nation_id, resp, world)
                             if event:
                                 self.global_events.append(event)
                                 self._add_event_to_relationships(turn, nation_id, event)

                # 2. Process main action
                if envelope.foreign_payload.action_type:
                    event = self._behavior_to_event(turn, nation_id, envelope.foreign_payload, world)
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
        """
        Convert a behavior to a notable event if significant.
        
        Design principle: Events are "newsworthy" outcomes visible to all nations.
        - Proposals do NOT generate events (internal)
        - Acceptances/Rejections DO generate events (visible outcomes)
        - Trade proposals generate TRADE_DEAL because acceptance is automatic via oracle
        - MOVE_TROOPS to enemy territory generates ATTACK event
        """
        action_type = behavior.action_type if hasattr(behavior, 'action_type') else str(type(behavior).__name__)
        # Convert enum to string if needed
        if hasattr(action_type, 'value'):
            action_type = action_type.value
        
        nation_name = world.nations[nation_id].name if nation_id in world.nations else nation_id
        params = getattr(behavior, 'parameters', {}) or {}
        
        # === IMMEDIATE WORLD NEWS EVENTS ===
        
        # War declaration (always newsworthy on SUCCESS)
        if "FORMAL_DECLARATION_OF_WAR" in action_type:
            outcome = getattr(behavior, "execution_outcome", None)
            if outcome and outcome.status != "SUCCESS":
                return None
                
            target_id = getattr(behavior, 'target_nation_id', None)
            target_name = world.nations[target_id].name if target_id and target_id in world.nations else target_id
            
            message = getattr(behavior, 'message', None)
            summary = f"{nation_name} declared war on {target_name}"
            if message:
                summary += f" (Message: '{message}')"
                
            return NotableEvent(
                turn=turn,
                event_type=EventType.WAR_DECLARED,
                actors=[nation_id, target_id] if target_id else [nation_id],
                summary=summary,
                relevance_to=None  # Global event
            )
        
        # Nuclear strike (always newsworthy - global catastrophe)
        if "NUCLEAR_OPTION" in action_type:
            target_province_id = params.get('target_province_id')
            target_nation = None
            if target_province_id and target_province_id in world.provinces:
                target_nation = world.provinces[target_province_id].owner_id
            target_name = world.nations[target_nation].name if target_nation and target_nation in world.nations else "unknown"
            return NotableEvent(
                turn=turn,
                event_type=EventType.NUCLEAR_STRIKE,
                actors=[nation_id, target_nation] if target_nation else [nation_id],
                summary=f"{nation_name} launched nuclear strike on {target_name}",
                relevance_to=None  # Global
            )
        
        # Treaty broken (always newsworthy - trust implications)
        if "BREAK_TREATY" in action_type:
            outcome = getattr(behavior, "execution_outcome", None)
            if outcome and outcome.status != "SUCCESS":
                return None

            target_id = getattr(behavior, 'target_nation_id', None)
            target_name = world.nations[target_id].name if target_id and target_id in world.nations else target_id
            
            message = getattr(behavior, 'message', None)
            summary = f"{nation_name} broke alliance with {target_name}"
            if message:
                summary += f" (Message: '{message}')"
                
            return NotableEvent(
                turn=turn,
                event_type=EventType.ALLIANCE_BROKEN,
                actors=[nation_id, target_id] if target_id else [nation_id],
                summary=summary,
                relevance_to=None  # Global
            )
        
        # Diplomatic messages
        if "SEND_DIPLOMATIC_MESSAGE" in action_type:
            outcome = getattr(behavior, "execution_outcome", None)
            if outcome and outcome.status != "SUCCESS":
                return None

            target_id = str(getattr(behavior, 'target_nation_id', ''))
            if not target_id or target_id == 'None':
                target_id = None

            target_name = target_id
            if target_id and target_id in world.nations:
                target_name = world.nations[target_id].name
            elif target_id and str(target_id) in world.nations:
                 target_name = world.nations[str(target_id)].name

            msg_type = getattr(behavior, 'diplomatic_message_type', 'MESSAGE')
            message = getattr(behavior, 'message', None)
            
            summary = f"{nation_name} sent a {msg_type} to {target_name}"
            if message:
                summary += f" (Message: '{message}')"
                
            return NotableEvent(
                turn=turn,
                event_type=EventType.DIPLOMATIC_MESSAGE,
                actors=[nation_id, target_id] if target_id else [nation_id],
                summary=summary,
                relevance_to=[nation_id, target_id] if target_id else [nation_id]
            )
            
        # Proposals and responses
        if any(x in action_type for x in ["PROPOSE_ALLIANCE", "REQUEST_PEACE", "ACCEPT_PROPOSAL", "REJECT_PROPOSAL"]):
            target_id = str(getattr(behavior, 'target_nation_id', ''))
            if not target_id or target_id == 'None':
                target_id = None
            
            target_name = target_id
            if target_id and target_id in world.nations:
                target_name = world.nations[target_id].name
            elif target_id and str(target_id) in world.nations: # Handle int-as-string keys
                 target_name = world.nations[str(target_id)].name

            message = getattr(behavior, 'message', None)
            
            event_type = None
            if "ACCEPT_PROPOSAL" in action_type:
                # If handled by response details, skip here to avoid duplication
                outcome = getattr(behavior, "execution_outcome", None)
                if outcome and outcome.details and "responses" in outcome.details:
                    # Check if any response generated a valid event (implied yes if formatted correctly)
                    # We assume _extract_events handled it.
                    return None

                ref = str(getattr(behavior, 'proposal_ref_type', '') or '').upper()
                event_type = EventType.PEACE_SIGNED if "PEACE" in ref else EventType.ALLIANCE_FORMED
            elif "REJECT_PROPOSAL" in action_type:
                ref = str(getattr(behavior, 'proposal_ref_type', '') or '').upper()
                event_type = EventType.PEACE_REJECTED if "PEACE" in ref else EventType.ALLIANCE_REJECTED
            
            # NOTE: Proposal events (PROPOSE_ALLIANCE, REQUEST_PEACE) are now handled directly 
            # by the Action Handler to ensure they only appear if successful.
            # We skip them here to avoid "phantom" events for blocked actions.
            
            summary = f"{nation_name} {action_type.replace('_', ' ').lower()} with {target_name}"
            if message:
                summary += f" (Message: '{message}')"
            
            if event_type:
                # Deduplication: Check if identical event exists this turn
                for existing in self.global_events:
                    if (existing.turn == turn and 
                        existing.event_type == event_type and 
                        set(existing.actors) == {nation_id, target_id}):
                        return None

                return NotableEvent(
                    turn=turn,
                    event_type=event_type,
                    actors=[nation_id, target_id] if target_id else [nation_id],
                    summary=summary,
                    relevance_to=[nation_id, target_id] if target_id else [nation_id]
                )
            return None
        
        # === TRADE (auto-accepted via oracle, so proposal = deal) ===
        if "TRADE_PROPOSAL" in action_type:
            outcome = getattr(behavior, "execution_outcome", None)
            if not outcome or outcome.status != "SUCCESS":
                return None

            target_id = str(getattr(behavior, 'target_nation_id', ''))
            if not target_id or target_id == 'None':
                target_id = None

            target_name = target_id
            if target_id and target_id in world.nations:
                target_name = world.nations[target_id].name
            elif target_id and str(target_id) in world.nations:
                 target_name = world.nations[str(target_id)].name
            
            message = getattr(behavior, 'message', None)
            summary = f"{nation_name} established trade with {target_name}"
            if message:
                summary += f" (Message: '{message}')"
                
            return NotableEvent(
                turn=turn,
                event_type=EventType.TRADE_DEAL,
                actors=[nation_id, target_id] if target_id else [nation_id],
                summary=summary,
                relevance_to=None  # Global - all nations see trade deals
            )
        
        # === NUCLEAR STRIKE ===
        if "NUCLEAR_OPTION" in action_type:
            outcome = getattr(behavior, "execution_outcome", None)
            if outcome and outcome.status == "SUCCESS":
                target_province_id = params.get('target_province_id')
                target_nation_id = params.get('target_nation_id')
                return NotableEvent(
                    turn=turn,
                    event_type=EventType.NUCLEAR_STRIKE,
                    actors=[nation_id, target_nation_id] if target_nation_id else [nation_id],
                    summary=f"☢️ CRITICAL: {nation_name} launched a nuclear strike on {target_nation_id}!",
                    relevance_to=None # Global
                )
        
        # === MILITARY MOVEMENT (newsworthy only if attacking enemy) ===
        if "MOVE_TROOPS" in action_type:
            to_province_id = params.get('to_province_id')
            if to_province_id and to_province_id in world.provinces:
                to_province = world.provinces[to_province_id]
                target_owner = to_province.owner_id
                
                # Check if target is enemy (not own, not allied)
                if target_owner and target_owner != nation_id:
                    # NEW: Check if the action was actually successful
                    outcome = getattr(behavior, "execution_outcome", None)
                    if outcome and outcome.status != "SUCCESS":
                        return None
                        
                    relationship = world.relationship_matrix.get(nation_id, {}).get(target_owner, "PEACE")
                    
                    if relationship == "WAR":
                        # Moving into enemy territory during war = ATTACK
                        target_name = world.nations[target_owner].name if target_owner in world.nations else target_owner
                        return NotableEvent(
                            turn=turn,
                            event_type=EventType.ATTACK,
                            actors=[nation_id, target_owner],
                            summary=f"{nation_name} attacked {target_name} territory",
                            relevance_to=None  # Global
                        )
                    elif relationship != "ALLIANCE":
                        # Moving troops near non-allied nation = TROOPS_MOBILIZED (threatening)
                        target_name = world.nations[target_owner].name if target_owner in world.nations else target_owner
                        return NotableEvent(
                            turn=turn,
                            event_type=EventType.TROOPS_MOBILIZED,
                            actors=[nation_id, target_owner],
                            summary=f"{nation_name} moved troops near {target_name} border",
                            relevance_to=target_owner  # Specifically concerning to neighbor
                        )
            
            # COMBAT_RESULT (if outcome has battle details)
            outcome = getattr(behavior, "execution_outcome", None)
            if outcome and hasattr(outcome, "details") and outcome.details:
                details = outcome.details
                if "attacker_wins" in details:
                    winner = nation_name if details["attacker_wins"] else "Defender"
                    msg = f"Battle Result: {winner} won!"
                    if "attacker_losses" in details or "defender_losses" in details:
                        a_loss = details.get("attacker_losses", 0)
                        d_loss = details.get("defender_losses", 0)
                        msg += f" (Losses: Attacker {a_loss}, Defender {d_loss})"
                    
                    target_id = getattr(behavior, 'target_nation_id', None)
                    return NotableEvent(
                        turn=turn,
                        event_type=EventType.COMBAT_RESULT,
                        actors=[nation_id, target_id] if target_id else [nation_id],
                        summary=msg,
                        relevance_to=None # Global
                    )
        
        # === NO EVENT for internal actions ===
        # PROPOSE_ALLIANCE, REQUEST_PEACE, CREATE_UNIT, INVEST_WELFARE, etc.
        # These are internal and don't generate world news
        
        return None
    
    def _response_detail_to_event(
        self, 
        turn: int, 
        nation_id: str, 
        resp: Dict[str, Any],
        world: WorldState
    ) -> Optional[NotableEvent]:
        """Convert a proposal response detail to a global event."""
        event_type_str = resp.get("event_type")
        if not event_type_str:
            return None
            
        target_id = resp.get("target_id")
        target_name = world.nations[target_id].name if target_id and target_id in world.nations else target_id
        nation_name = world.nations[nation_id].name if nation_id in world.nations else nation_id
        
        # Map raw strings from handler to EventType
        if event_type_str == "UPGRADED":
            event_type = EventType.ALLIANCE_UPGRADED
        elif event_type_str == "DOWNGRADED":
            event_type = EventType.ALLIANCE_DOWNGRADED
        elif event_type_str == "FORMED":
            event_type = EventType.ALLIANCE_FORMED
        else:
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                return None # Unknown event type
            
        summary = ""
        if event_type == EventType.ALLIANCE_UPGRADED:
            summary = f"{nation_name} UPGRADED alliance with {target_name}"
        elif event_type == EventType.ALLIANCE_DOWNGRADED:
             summary = f"{nation_name} DOWNGRADED alliance with {target_name}"
        elif event_type == EventType.ALLIANCE_FORMED:
             summary = f"{nation_name} formed alliance with {target_name}"
        else:
            # Other types?
            return None
            
        return NotableEvent(
            turn=turn,
            event_type=event_type,
            actors=[nation_id, target_id] if target_id else [nation_id],
            summary=summary,
            relevance_to=[nation_id, target_id] if target_id else [nation_id]
        )
    
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
            
            # Defense: Multiple moves
            if envelope.defense_payload:
                for move in envelope.defense_payload.moves:
                    action = self._behavior_to_action(turn, move)
                    if action:
                        self.nation_actions[nation_id].append(action)
            
            # Economy: Single action
            if envelope.economic_payload and envelope.economic_payload.action_type:
                action = self._behavior_to_action(turn, envelope.economic_payload)
                if action:
                    self.nation_actions[nation_id].append(action)
            
            # Foreign: Single action
            if envelope.foreign_payload and envelope.foreign_payload.action_type:
                action = self._behavior_to_action(turn, envelope.foreign_payload)
                if action:
                    self.nation_actions[nation_id].append(action)

    def _log_presidential_decisions(self, turn: int, envelopes: List[Any]) -> None:
        """Log President decisions (Approvals/Vetos) to action history."""
        from geomas.actions.common import Decision
        
        for envelope in envelopes:
            nation_id = envelope.sender_id
            if nation_id not in self.nation_actions:
                self.nation_actions[nation_id] = []
            
            # 1. Defense Decision
            if hasattr(envelope, 'defense_payload') and envelope.defense_payload:
                status = "APPROVED" if envelope.defense_payload.decision == Decision.APPROVE else "VETOED"
                if envelope.defense_payload.decision == Decision.APPROVE:
                    move_count = len(envelope.defense_payload.moves)
                    summary = f"APPROVED Defense proposal ({move_count} actions)"
                else:
                    summary = "VETOED Defense proposal"
                
                self.nation_actions[nation_id].append(MyAction(
                    turn=turn, domain="President", action_type="DECISION_DEFENSE",
                    action_summary=summary, outcome=status,
                    reasoning=envelope.defense_private_reasoning
                ))

            # 2. Economy Decision
            if hasattr(envelope, 'economic_payload') and envelope.economic_payload:
                status = "APPROVED" if envelope.economic_payload.decision == Decision.APPROVE else "VETOED"
                if envelope.economic_payload.decision == Decision.APPROVE:
                    act_type = envelope.economic_payload.action_type
                    if hasattr(act_type, 'value'): act_type = act_type.value
                    summary = f"APPROVED Economy proposal: {act_type}"
                else:
                    summary = "VETOED Economy proposal"
                
                self.nation_actions[nation_id].append(MyAction(
                    turn=turn, domain="President", action_type="DECISION_ECONOMY",
                    action_summary=summary, outcome=status,
                    reasoning=None  # Economic intent removed, no private reasoning
                ))

            # 3. Foreign Decision
            if hasattr(envelope, 'foreign_payload') and envelope.foreign_payload:
                status = "APPROVED" if envelope.foreign_payload.decision == Decision.APPROVE else "VETOED"
                if envelope.foreign_payload.decision == Decision.APPROVE:
                    act_type = envelope.foreign_payload.action_type
                    if hasattr(act_type, 'value'): act_type = act_type.value
                    summary = f"APPROVED Foreign proposal: {act_type}"
                else:
                    summary = "VETOED Foreign proposal"
                
                self.nation_actions[nation_id].append(MyAction(
                    turn=turn, domain="President", action_type="DECISION_FOREIGN",
                    action_summary=summary, outcome=status,
                    reasoning=envelope.foreign_private_reasoning
                ))

    def get_presidential_feedback(self, nation_id: str, domain: str, limit: int = 10) -> str:
        """
        Get formatted feedback from President on past proposals.
        
        Args:
            nation_id: Nation ID
            domain: "Defense", "Economy", "Foreign" (Matches DECISION_{DOMAIN})
            limit: Max items
            
        Returns:
            Formatted string section (markdown)
        """
        target_type = f"DECISION_{domain.upper()}"
        
        if nation_id not in self.nation_actions:
            return ""
            
        # Filter for President decisions in this domain
        actions = [
            a for a in self.nation_actions[nation_id] 
            if a.domain == "President" and a.action_type == target_type
        ]
        
        # Sort by turn descending (newest first)
        actions.sort(key=lambda a: a.turn, reverse=True)
        actions = actions[:limit]
        
        if not actions:
            return ""
            
        lines = [f"## Presidential Feedback ({domain})"]
        for a in actions:
            icon = "✅" if a.outcome == "APPROVED" else "❌"
            reasoning = a.reasoning if a.reasoning else "No reasoning provided."
            lines.append(f"- **T{a.turn} {icon} {a.outcome}**: {reasoning}")
            
        return "\n".join(lines)
    
    def _behavior_to_action(self, turn: int, behavior: Any) -> Optional[MyAction]:
        """Convert behavior to MyAction record with descriptive summaries."""
        action_type = behavior.action_type if hasattr(behavior, 'action_type') else str(type(behavior).__name__)
        
        # Convert enum to string if needed
        action_type_str = action_type.value if hasattr(action_type, 'value') else str(action_type)
        
        # Determine domain based on actual action enum values
        # Defense: MOVE_TROOPS, CREATE_UNIT, NUCLEAR_OPTION
        if any(x in action_type_str for x in ["MOVE_TROOPS", "CREATE_UNIT", "NUCLEAR_OPTION"]):
            domain = "Defense"
        # Economy: INVEST_WELFARE, TRADE_PROPOSAL, RAISE_WAR_TAX
        elif any(x in action_type_str for x in ["INVEST_WELFARE", "TRADE_PROPOSAL", "RAISE_WAR_TAX"]):
            domain = "Economy"
        # Foreign: SEND_DIPLOMATIC_MESSAGE, PROPOSE_ALLIANCE, FORMAL_DECLARATION_OF_WAR, etc.
        elif any(x in action_type_str for x in ["PROPOSE_ALLIANCE", "FORMAL_DECLARATION_OF_WAR", 
                                             "BREAK_TREATY", "REQUEST_PEACE", 
                                             "ACCEPT_PROPOSAL", "REJECT_PROPOSAL",
                                             "SEND_DIPLOMATIC_MESSAGE"]):
            domain = "Foreign"
        else:
            domain = "Other"
        
        # Build descriptive summary based on action type and domain
        summary = self._build_action_summary(behavior, action_type_str, domain)
        execution_outcome = getattr(behavior, 'execution_outcome', None)
        outcome_str = execution_outcome.status if execution_outcome else "SUCCESS"
        outcome_reason = execution_outcome.reason if execution_outcome else None
        
        # Capture reasoning from the payload if present (for Ministers)
        reasoning = getattr(behavior, 'reasoning', None)
        
        return MyAction(
            turn=turn,
            domain=domain,
            action_type=action_type_str,
            action_summary=summary,
            outcome=outcome_str,
            outcome_reason=outcome_reason,
            reasoning=reasoning
        )
    
    def _build_action_summary(self, behavior: Any, action_type: str, domain: str) -> str:
        """Build descriptive summary from action fields."""
        # Defense actions — use explicit fields
        if "MOVE_TROOPS" in action_type:
            unit_type = getattr(behavior, 'unit_type', None)
            quantity = getattr(behavior, 'quantity', None)
            source = getattr(behavior, 'source_province_id', None)
            target = getattr(behavior, 'target_province_id', None)
            target_nation = getattr(behavior, 'target_nation_id', None)
            
            unit_str = unit_type.value if hasattr(unit_type, 'value') else str(unit_type or 'units')
            qty_str = f"{quantity}x " if quantity else ""
            route = f"from {source} → {target}" if source and target else f"to {target}" if target else ""
            
            # Check if this is an attack (target owned by someone else)
            if target_nation and target_nation != getattr(behavior, '_nation_id', None):
                return f"Moved {qty_str}{unit_str} {route}"
            return f"Moved {qty_str}{unit_str} {route}"
        
        if "CREATE_UNIT" in action_type:
            unit_type = getattr(behavior, 'unit_type', None)
            quantity = getattr(behavior, 'quantity', None)
            target = getattr(behavior, 'target_province_id', None)
            
            unit_str = unit_type.value if hasattr(unit_type, 'value') else str(unit_type or 'units')
            qty_str = f"{quantity}x " if quantity else ""
            loc_str = f" at province {target}" if target else ""
            return f"Created {qty_str}{unit_str}{loc_str}"
        
        if "NUCLEAR_OPTION" in action_type:
            target = getattr(behavior, 'target_province_id', None)
            target_nation = getattr(behavior, 'target_nation_id', None)
            return f"Launched nuclear strike on province {target} ({target_nation})"
        
        # Economy actions
        if "INVEST_WELFARE" in action_type:
            amount = getattr(behavior, 'amount', None)
            return f"Invested {amount:.0f} in welfare" if amount else "Invested in welfare"
        
        if "TRADE_PROPOSAL" in action_type:
            target = getattr(behavior, 'target_nation_id', None)
            give_type = getattr(behavior, 'give_type', None)
            give_amount = getattr(behavior, 'give_amount', None)
            want_type = getattr(behavior, 'want_type', None)
            if give_type and give_amount and want_type:
                return f"Trade with {target}: give {give_amount:.0f} {give_type} for {want_type}"
            return f"Trade proposal to {target}"
        
        if "RAISE_WAR_TAX" in action_type:
            return "Raised war tax"
        
        # Foreign actions
        if "FORMAL_DECLARATION_OF_WAR" in action_type:
            target = getattr(behavior, 'target_nation_id', None)
            return f"Declared war on {target}"
        
        if "PROPOSE_ALLIANCE" in action_type:
            target = getattr(behavior, 'target_nation_id', None)
            return f"Proposed alliance to {target}"
        
        if "REQUEST_PEACE" in action_type:
            target = getattr(behavior, 'target_nation_id', None)
            return f"Requested peace with {target}"
        
        if "SEND_DIPLOMATIC_MESSAGE" in action_type:
            target = getattr(behavior, 'target_nation_id', None)
            msg_type = getattr(behavior, 'diplomatic_message_type', None)
            msg_str = msg_type.value if hasattr(msg_type, 'value') else str(msg_type or '')
            return f"Sent {msg_str} to {target}"
        
        # Fallback
        message = getattr(behavior, 'message', None)
        summary = action_type
        if message:
            summary += f" [{message[:50]}]"
        return summary
    
    def _prune_if_needed(self) -> None:
        """Prune old events and actions to stay within budget."""
        # Note: We do NOT prune global_events anymore to keep full history for UI.
        # Agent context budget is handled by get_events_for limit.
        
        
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
                limit = self.MAX_ACTIONS_PRESIDENT if domain == "President" else self.MAX_ACTIONS_PER_DOMAIN
                pruned.extend(domain_actions[-limit:])
            
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
    
    def get_events_for(
        self, 
        nation_id: str, 
        current_turn: int,
        max_events: int = 15,
        event_types: Optional[List[EventType]] = None
    ) -> List[str]:
        """
        Get formatted event lines relevant to a nation.
        
        Args:
            nation_id: Nation to get events for
            current_turn: Current turn of the simulation used for expiry logic
            max_events: Maximum events to return
            event_types: Optional list of EventTypes to filter by
            
        Returns:
            List of formatted event strings
        """
        relevant = []
        
        for event in self.global_events:
            # Expiry logic for Genesis/Startup events
            if getattr(event, 'turn', 1) <= 0 and current_turn > 5:
                continue
                
            # Domain filter if provided
            if event_types and event.event_type not in event_types:
                continue
                
            # Relevance filter: Include if: global, or involves this nation, or relevant to this nation
            if (event.relevance_to is None or 
                (isinstance(event.relevance_to, list) and nation_id in event.relevance_to) or
                (isinstance(event.relevance_to, str) and event.relevance_to == nation_id) or
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
