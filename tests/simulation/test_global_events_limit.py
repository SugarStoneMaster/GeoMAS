
import pytest
from geomas.agents.context.events.context_manager import ContextManager
from geomas.agents.context.events.schemas import NotableEvent, EventType

def test_global_events_limit_reproduction():
    """
    Test that global_events are currently capped at 50.
    After the fix, this test should be updated to assert > 50.
    """
    # 1. Initialize ContextManager
    cm = ContextManager()
    
    # 2. Add 60 events
    for i in range(60):
        event = NotableEvent(
            turn=1,
            event_type=EventType.DIPLOMATIC_MESSAGE, # Non-critical
            summary=f"Event {i}",
            actors=["A", "B"]
        )
        cm.global_events.append(event)
        
    # 3. Trigger Pruning
    cm._prune_if_needed()
    
    # 4. Verify Limit (Current Behavior is 50)
    # AFTER FIX: We expect 60 events (no truncation)
    assert len(cm.global_events) == 60, f"Expected 60 events, but got {len(cm.global_events)}"

def test_no_data_loss_after_fix():
    """
    This test will fail effectively until the fix is applied.
    It expects full history retention.
    """
    cm = ContextManager()
    
    # Add 100 events
    total = 100
    for i in range(total):
        event = NotableEvent(
            turn=i,
            event_type=EventType.DIPLOMATIC_MESSAGE, # Non-critical
            summary=f"Event {i}",
            actors=["A"]
        )
        cm.global_events.append(event)
        
    cm._prune_if_needed()
    
    # We WANT this to be total (100), but currently it will be 50.
    # So this assertion is what we aim for.
    # Validation: checks that *oldest* event is still present (Turn 0)
    
    # If pruning happens, it keeps most recent, so Turn 0 would be lost.
    has_turn_0 = any(e.turn == 0 for e in cm.global_events)
    
    assert len(cm.global_events) == total, "Global events were truncated!"
    assert has_turn_0, "Oldest event was lost!"
