"""
Tests for NationAgent and President Gatekeeper logic.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from geomas.world import generate_world
from geomas.agents.nation_agent import NationAgent
from geomas.agents.schemas import (
    GlobalStrategy,
    DefenseProposal, DefenseIntent, DefenseIntentType, 
    EconomicProposal,
    ForeignProposal, ForeignIntent, ForeignIntentType,
    PresidentialDecree, Decision, DefenseDecree, EconomicDecree, ForeignDecree
)
from geomas.actions.defense import DefensePayload
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload
from geomas.actions.common import Decision
from geomas.agents.llm_client import LLMClient


from geomas.actions.defense.schemas import DefenseActionType, DefenseActionItem
from geomas.actions.economy.schemas import EconomicActionType
from geomas.actions.foreign.schemas import ForeignActionType

class TestNationAgent:
    
    @pytest.fixture
    def setup(self):
        world = generate_world(seed=42, n_cells=20, n_nations=1)
        nation_id = list(world.nations.keys())[0]
        client = MagicMock(spec=LLMClient)
        # Configure client.aquery_agent as AsyncMock for minister proposals
        client.aquery_agent = AsyncMock()
        # Configure client.query_agent for legacy/president (sync)
        client.query_agent = MagicMock()
        agent = NationAgent(nation_id, world, client)
        
        return agent, client
    
    def test_act_approve_flow(self, setup):
        """Test standard flow where President approves minister proposals."""
        agent, client = setup
        
        # 1. Setup Minister Proposals
        def_prop = DefenseProposal(
            intent=DefenseIntent(
                public_intent=DefenseIntentType.DEFENSE,
                private_intent=DefenseIntentType.DEFENSE,
                reasoning="Defend"
            ),
            # Corrected DefensePayload (only has moves)
            payload=DefensePayload(decision=Decision.APPROVE, moves=[])
        )
        eco_prop = EconomicProposal(
            payload=EconomicPayload(decision=Decision.APPROVE)
        )
        for_prop = ForeignProposal(
            intent=ForeignIntent(
                public_intent=ForeignIntentType.IDLE,
                private_intent=ForeignIntentType.IDLE,
                reasoning="Chill"
            ),
            payload=ForeignPayload(decision=Decision.APPROVE)
        )
        
        # 2. Setup President Decree (APPROVE ALL)
        decree = PresidentialDecree(
            defense=DefenseDecree(action=Decision.APPROVE, reasoning="Good"),
            economy=EconomicDecree(action=Decision.APPROVE, reasoning="Good"),
            foreign=ForeignDecree(action=Decision.APPROVE, reasoning="Good"),
            
            public_statement="We are strong.",
            
            defense_public_intent=DefenseIntentType.DEFENSE,
            defense_private_intent=DefenseIntentType.DEFENSE,
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
            
            defense_private_reasoning="R1",
            foreign_private_reasoning="R3"
        )
        
        # Mock side_effect
        # aquery_agent will be called for 3 minister proposals
        client.aquery_agent.side_effect = [def_prop, eco_prop, for_prop]
        # query_agent will be called ONCE for President
        client.query_agent.return_value = decree
        
        # ACT
        envelope = agent.act(turn=1)
        
        # ASSERT
        assert envelope.sender_id == agent.id
        assert envelope.defense_payload == def_prop.payload
        assert envelope.defense_payload.decision == Decision.APPROVE
        
        # Verify summaries in President prompt (client.query_agent was called with briefing data)
        args, _ = client.query_agent.call_args # Last call was President
        system_prompt, user_prompt, schema = args
        assert "Defense Minister" in user_prompt
        assert "**Public Intent:** DEFENSE" in user_prompt

    def test_act_veto_flow(self, setup):
        """Test flow where President vetoes a minister."""
        agent, client = setup
        world = agent.world
        
        # Minister Props (Defense wants to attack)
        def_prop = DefenseProposal(
            intent=DefenseIntent(
                public_intent=DefenseIntentType.CONQUEST,
                private_intent=DefenseIntentType.CONQUEST,
                reasoning="Attack!"
            ),
            payload=DefensePayload(
                decision=Decision.APPROVE, 
                moves=[
                    DefenseActionItem(
                        priority=1, 
                        action_type=DefenseActionType.MOVE_TROOPS,
                        source_province_id=1,
                        target_province_id=2
                    )
                ]
            ), 
            urgency=10
        )
        eco_prop = EconomicProposal(
            payload=EconomicPayload(decision=Decision.APPROVE), 
            projected_cost=0
        )
        for_prop = ForeignProposal(
            intent=ForeignIntent(
                public_intent=ForeignIntentType.IDLE,
                private_intent=ForeignIntentType.IDLE,
                reasoning="."
            ),
            payload=ForeignPayload(decision=Decision.APPROVE), 
            target_trust_impact=0
        )
        
        # President Decree (VETO Defense)
        decree = PresidentialDecree(
            defense=DefenseDecree(
                action=Decision.VETO, 
                reasoning="Too dangerous!"
            ),
            economy=EconomicDecree(action=Decision.APPROVE, reasoning="Ok"),
            foreign=ForeignDecree(action=Decision.APPROVE, reasoning="Ok"),
            
            public_statement="We choose peace.",
            
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE, 
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
            
            defense_private_reasoning="Avoid war.",
            foreign_private_reasoning="."
        )
        
        # Mock LLM returns
        # Mock LLM returns
        client.aquery_agent.side_effect = [def_prop, eco_prop, for_prop]
        client.query_agent.return_value = decree
        
        # ACT
        envelope = agent.act(turn=1)
        
        # ASSERT
        # Defense should be VETOED -> IDLE
        assert envelope.defense_payload.decision == Decision.VETO
        assert envelope.defense_payload.moves == [] # Should be empty
        
        # Economy/Foreign should be APPROVED -> APPROVE
        assert envelope.economic_payload.decision == Decision.APPROVE

    def test_act_acknowledge_flow(self, setup):
        """Test flow where President correctly acknowledges IDLE ministers."""
        agent, client = setup
        
        # 1. Setup Minister Proposals (All IDLE)
        def_prop = DefenseProposal(
            intent=DefenseIntent(
                public_intent=DefenseIntentType.IDLE,
                private_intent=DefenseIntentType.IDLE,
                reasoning="Nothing to do."
            ),
            payload=DefensePayload(decision=Decision.APPROVE, moves=[])
        )
        eco_prop = EconomicProposal(
            payload=EconomicPayload(decision=Decision.APPROVE, action_type=EconomicActionType.IDLE)
        )
        for_prop = ForeignProposal(
            intent=ForeignIntent(
                public_intent=ForeignIntentType.IDLE,
                private_intent=ForeignIntentType.IDLE,
                reasoning="Nothing to do."
            ),
            payload=ForeignPayload(decision=Decision.APPROVE, action_type=ForeignActionType.IDLE)
        )
        
        # 2. Setup President Decree (ACKNOWLEDGE ALL)
        from geomas.agents.schemas.protocol import PresidentialDecision
        decree = PresidentialDecree(
            defense=DefenseDecree(action=PresidentialDecision.ACKNOWLEDGE, reasoning="Acknowledged defense inactivity"),
            economy=EconomicDecree(action=PresidentialDecision.ACKNOWLEDGE, reasoning="Acknowledged economic inactivity"),
            foreign=ForeignDecree(action=PresidentialDecision.ACKNOWLEDGE, reasoning="Acknowledged diplomatic inactivity"),
            
            public_statement="We are observing a period of stability.",
            
            defense_public_intent=DefenseIntentType.IDLE,
            defense_private_intent=DefenseIntentType.IDLE,
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
            
            defense_private_reasoning="Monitoring borders.",
            foreign_private_reasoning="Monitoring relations."
        )
        
        client.aquery_agent.side_effect = [def_prop, eco_prop, for_prop]
        client.query_agent.return_value = decree
        
        # ACT
        envelope = agent.act(turn=1)
        
        # ASSERT
        # ACKNOWLEDGE should safely parse into non-VETO SUCCESS IDLE states (effectively APPROVE locally, mapped as IDLE)
        assert envelope.defense_payload.decision == Decision.APPROVE
        assert envelope.defense_payload.moves == []
        
        assert envelope.economic_payload.decision == Decision.APPROVE
        assert envelope.economic_payload.action_type == EconomicActionType.IDLE
        
        assert envelope.foreign_payload.decision == Decision.APPROVE
        assert envelope.foreign_payload.action_type == ForeignActionType.IDLE
        
        # Ensure reasoning captures the acknowledgement
        assert "ACKNOWLEDGED IDLE" in envelope.defense_private_reasoning
        assert "ACKNOWLEDGED IDLE" in envelope.foreign_private_reasoning
