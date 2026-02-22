
import pytest
from unittest.mock import MagicMock
from geomas.agents.context.events.context_manager import ContextManager
from geomas.agents.context.input import DefenseInputBuilder
from geomas.schemas.world import WorldState, NationState
from geomas.agents.schemas import CountryEnvelope, DefensePayload
from geomas.actions.common import Decision

class TestFeedbackLoop:
    
    def test_context_manager_stores_reasoning(self):
        """Verify ContextManager extracts and stores reasoning."""
        cm = ContextManager()
        
        # Mock Envelope with Defense Decision
        envelope = MagicMock(spec=CountryEnvelope)
        envelope.sender_id = "nation_a"
        
        # Setup Defense Payload
        envelope.defense_payload = MagicMock(spec=DefensePayload)
        envelope.defense_payload.decision = Decision.VETO
        envelope.defense_payload.moves = []
        
        # Setup Reasoning
        envelope.defense_private_reasoning = "VETOED: Too expensive."
        
        # Setup other payloads as None/Empty to avoid errors
        envelope.economic_payload = None
        envelope.foreign_payload = None
        
        # Update
        world = MagicMock(spec=WorldState)
        world.nations = {"nation_a": MagicMock()}
        world.global_events = []
        
        cm.update_after_turn(turn=1, envelopes=[envelope], world=world)
        
        # Verify Action Storage
        actions = cm.nation_actions["nation_a"]
        assert len(actions) == 1
        action = actions[0]
        assert action.domain == "President"
        assert action.action_type == "DECISION_DEFENSE"
        assert action.outcome == "VETOED"
        assert action.reasoning == "VETOED: Too expensive."
        
    def test_get_presidential_feedback_formatting(self):
        """Verify feedback string formatting."""
        cm = ContextManager()
        
        # Manually add actions
        from geomas.agents.context.events.schemas import MyAction
        cm.nation_actions["nation_a"] = [
            MyAction(
                turn=1, domain="President", action_type="DECISION_DEFENSE",
                action_summary="VETOED", outcome="VETOED",
                reasoning="Too risky."
            ),
            MyAction(
                turn=2, domain="President", action_type="DECISION_DEFENSE",
                action_summary="APPROVED", outcome="APPROVED",
                reasoning="Good plan."
            )
        ]
        
        feedback = cm.get_presidential_feedback("nation_a", "Defense")
        
        assert "## Presidential Feedback (Defense)" in feedback
        assert "**T2 ✅ APPROVED**: Good plan." in feedback
        assert "**T1 ❌ VETOED**: Too risky." in feedback
        
    def test_input_builder_includes_feedback(self):
        """Verify DefenseInputBuilder includes the feedback section."""
        # Setup World
        world = MagicMock(spec=WorldState)
        world.turn = 2
        nation = MagicMock(spec=NationState)
        nation.name = "Nation A"
        nation.public_satisfaction = 50.0
        nation.total_budget = 1000
        nation.power_projection = 10.0
        nation.total_food = 100
        nation.total_energy = 100
        nation.total_materials = 100
        nation.province_ids = []
        nation.total_soldiers = 100
        nation.total_aircraft = 10
        nation.total_navy = 5
        # Mock dictionaries for attributes that are accessed as dicts
        world.nations = {"nation_a": nation}
        world.provinces = {}
        world.relationship_matrix = {}
        world.trust_matrix = {}
        world.global_events = []
        
        # Setup ContextManager with feedback
        cm = ContextManager()
        from geomas.agents.context.events.schemas import MyAction
        cm.nation_actions["nation_a"] = [
            MyAction(
                turn=1, domain="President", action_type="DECISION_DEFENSE",
                action_summary="VETOED", outcome="VETOED",
                reasoning="Test Reasoning."
            )
        ]
        
        # Build Input
        builder = DefenseInputBuilder(world)
        # Mock military translator to avoid complex setup
        builder.military_translator = MagicMock()
        builder.military_translator.generate_military_report.return_value = "Military Report"
        
        prompt = builder.build("nation_a", turn=2, context_manager=cm)
        
        assert "## Presidential Feedback (Defense)" in prompt
        assert "Test Reasoning." in prompt
