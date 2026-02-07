"""
Tests for NationAgent and President Gatekeeper logic.
"""

import pytest
from unittest.mock import MagicMock, patch
from geomas.world import generate_world
from geomas.agents.nation_agent import NationAgent
from geomas.agents.schemas import (
    GlobalStrategy,
    DefenseProposal, DefenseIntent, DefenseIntentType, 
    EconomicProposal, EconomicIntent, EconomicIntentType,
    ForeignProposal, ForeignIntent, ForeignIntentType,
    PresidentialDecree, DecreeAction, DefenseDecree, EconomicDecree, ForeignDecree
)
from geomas.actions.defense import DefensePayload
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload
from geomas.actions.common import DecisionSource
from geomas.agents.llm_client import LLMClient


class TestNationAgent:
    
    @pytest.fixture
    def setup(self):
        world = generate_world(seed=42, n_cells=20, n_nations=1)
        nation_id = list(world.nations.keys())[0]
        client = MagicMock(spec=LLMClient)
        agent = NationAgent(nation_id, world, client)
        return agent, client
    
    def test_act_approve_flow(self, setup):
        """Test standard flow where President approves minister proposals."""
        agent, client = setup
        
        # 1. Setup Minister Proposals
        def_prop = DefenseProposal(
            intent=DefenseIntent(type=DefenseIntentType.DEFENSE, reasoning="Defend"),
            # Corrected DefensePayload (only has moves)
            payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
            urgency=1
        )
        eco_prop = EconomicProposal(
            intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="Grow"),
            payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE),
            projected_cost=10
        )
        for_prop = ForeignProposal(
            intent=ForeignIntent(type=ForeignIntentType.IDLE, reasoning="Chill"),
            payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE),
            target_trust_impact=0
        )
        
        # 2. Setup President Decree (APPROVE ALL)
        decree = PresidentialDecree(
            defense=DefenseDecree(action=DecreeAction.APPROVE, reasoning="Good"),
            economy=EconomicDecree(action=DecreeAction.APPROVE, reasoning="Good"),
            foreign=ForeignDecree(action=DecreeAction.APPROVE, reasoning="Good"),
            
            global_strategy=GlobalStrategy.COALITION_BUILDER,
            public_statement="We are strong.",
            
            defense_public_intent=DefenseIntentType.DEFENSE,
            defense_private_intent=DefenseIntentType.DEFENSE,
            economic_public_intent=EconomicIntentType.GROWTH,
            economic_private_intent=EconomicIntentType.GROWTH,
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
            
            defense_private_reasoning="R1",
            economic_private_reasoning="R2",
            foreign_private_reasoning="R3"
        )
        
        # Mock side_effect to return proposals then decree
        # Order: Def, Eco, For, President (or parallel, but sequential in code)
        client.query_agent.side_effect = [def_prop, eco_prop, for_prop, decree]
        
        # ACT
        envelope = agent.act(turn=1)
        
        # ASSERT
        assert envelope.sender_id == agent.id
        assert envelope.defense_payload == def_prop.payload
        assert envelope.defense_payload.source == DecisionSource.MINISTRY_ADVICE
        
        # Verify summaries in President prompt
        args, _ = client.query_agent.call_args # Last call was President
        system_prompt, user_prompt, schema = args
        assert "Defense Minister" in user_prompt
        assert "**Intent:** DEFENSE" in user_prompt

    def test_act_override_flow(self, setup):
        """Test flow where President overrides a minister."""
        agent, client = setup
        
        # Minister Props
        def_prop = DefenseProposal(
            intent=DefenseIntent(type=DefenseIntentType.IDLE, reasoning="Sleep"),
            payload=DefensePayload(source=DecisionSource.MINISTRY_ADVICE, moves=[]),
            urgency=1
        )
        eco_prop = EconomicProposal(intent=EconomicIntent(type=EconomicIntentType.IDLE, reasoning="."), payload=EconomicPayload(source=DecisionSource.MINISTRY_ADVICE), projected_cost=0)
        for_prop = ForeignProposal(intent=ForeignIntent(type=ForeignIntentType.IDLE, reasoning="."), payload=ForeignPayload(source=DecisionSource.MINISTRY_ADVICE), target_trust_impact=0)
        
        # President Decree (OVERRIDE Defense)
        new_def_payload = DefensePayload(
            source=DecisionSource.PRESIDENT_OVERRIDE, # Will be enforced anyway
            moves=[]
        )
        
        decree = PresidentialDecree(
            defense=DefenseDecree(
                action=DecreeAction.OVERRIDE, 
                new_payload=new_def_payload,
                reasoning="Wake up!"
            ),
            economy=EconomicDecree(action=DecreeAction.APPROVE, reasoning="Ok"),
            foreign=ForeignDecree(action=DecreeAction.APPROVE, reasoning="Ok"),
            
            global_strategy=GlobalStrategy.COALITION_BUILDER,
            public_statement="emergency",
            
            defense_public_intent=DefenseIntentType.DETERRENCE,
            defense_private_intent=DefenseIntentType.CONQUEST, # Changed intent
            economic_public_intent=EconomicIntentType.IDLE,
            economic_private_intent=EconomicIntentType.IDLE,
            foreign_public_intent=ForeignIntentType.IDLE,
            foreign_private_intent=ForeignIntentType.IDLE,
            
            defense_private_reasoning="War",
            economic_private_reasoning=".",
            foreign_private_reasoning="."
        )
        
        client.query_agent.side_effect = [def_prop, eco_prop, for_prop, decree]
        
        # ACT
        envelope = agent.act(turn=1)
        
        # ASSERT
        assert envelope.defense_payload != def_prop.payload
        assert envelope.defense_payload == new_def_payload
        assert envelope.defense_payload.source == DecisionSource.PRESIDENT_OVERRIDE
