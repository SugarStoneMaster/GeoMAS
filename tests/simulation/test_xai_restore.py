
import pytest
import os
import asyncio
from unittest.mock import MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.agents.llm_client import LLMClient
from geomas.agents.schemas import (
    CountryEnvelope, GlobalStrategy, PresidentialDecision,
    DefensePayload, EconomicPayload, ForeignPayload,
    DefenseIntentType, ForeignIntentType,
    DefenseProposal, EconomicProposal, ForeignProposal,
    DefenseIntent, ForeignIntent
)
from geomas.actions.defense.schemas import DefenseProposalPayload
from geomas.actions.economy.schemas import EconomicProposalPayload, EconomicActionType
from geomas.actions.foreign.schemas import ForeignProposalPayload, ForeignActionType
from geomas.actions.common import Decision
from geomas.db import SimulationDB

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_sim.duckdb"
    return str(db_file)

def test_history_restoration_minimal(temp_db):
    """Verify that load_state restores simulation history from DB without running full steps."""
    # 1. Setup Simulation
    client = MagicMock(spec=LLMClient)
    sim = SimulationEngine(
        map_seed=42, 
        n_cells=100, 
        n_nations=4, 
        llm_client=client, 
        db_path=temp_db
    )
    
    # 2. Manually create an envelope and persist it
    envelope = CountryEnvelope(
        turn=1,
        sender_id="AGRIA",
        global_strategy=GlobalStrategy.COALITION_BUILDER,
        public_statement="Peace!",
        defense_payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
        defense_public_intent=DefenseIntentType.IDLE,
        defense_private_intent=DefenseIntentType.IDLE,
        defense_private_reasoning="None",
        economic_payload=EconomicPayload(decision=Decision.APPROVE, action_type=None),
        foreign_payload=ForeignPayload(decision=Decision.APPROVE, action_type=None),
        foreign_public_intent=ForeignIntentType.IDLE,
        foreign_private_intent=ForeignIntentType.IDLE,
        foreign_private_reasoning="None",
        last_input_prompt="TRACE_123"
    )
    
    sim._persist_envelopes(1, [envelope])
    
    # Also save snapshot for turn 2 (the turn we want to load)
    from geomas.db.serialization import serialize_world_snapshot
    snapshot = serialize_world_snapshot(sim.world)
    sim.db.save_snapshot(sim.simulation_id, 2, **snapshot)
    
    # 3. Create a NEW engine and load state from Turn 2
    sim.close()
    
    new_sim = SimulationEngine(
        map_seed=42, 
        n_cells=100, 
        n_nations=4, 
        llm_client=client, 
        db_path=temp_db,
        simulation_id=sim.simulation_id
    )
    
    new_sim.load_state(2)
    
    # 4. Verify History is restored
    assert len(new_sim.history) == 1
    assert new_sim.history[0][0].last_input_prompt == "TRACE_123"
    assert new_sim.world.turn == 2
    
    # NEW: Verify Trace History in Agent
    agent = new_sim.agents["AGRIA"]
    assert 1 in agent.trace_history
    assert agent.trace_history[1]["president"]["user_prompt"] == "TRACE_123"
    
    # NEW: Verify Opinion Trace History
    o_agent = new_sim.opinion_agents["AGRIA"]
    assert 1 in o_agent.trace_history
    assert o_agent.trace_history[1]["system_prompt"] is None # We didn't set it in mock envelope

def test_action_injection_parsing():
    """Verify that NationAgent correctly parses action-level injections."""
    from geomas.agents.nation_agent import NationAgent
    from geomas.schemas.world import WorldState, NationState
    
    world = MagicMock(spec=WorldState)
    nation = MagicMock(spec=NationState)
    nation.name = "Testland"
    world.nations = {"TEST": nation}
    
    client = MagicMock(spec=LLMClient)
    agent = NationAgent("TEST", world, client)
    
    injections = [
        {
            "nation_id": "TEST",
            "role": "Defense",
            "action": "MOVE_TROOPS",
            "details": "qty=50, to=91",
            "type": "FORCE"
        }
    ]
    
    actual_injections = []
    
    async def mock_cabinet(turn, def_inj, eco_inj, for_inj):
        actual_injections.append(def_inj)
        return (
            DefenseProposal(
                intent=DefenseIntent(public_intent=DefenseIntentType.IDLE, private_intent=DefenseIntentType.IDLE, reasoning="mock"),
                payload=DefenseProposalPayload(moves=[])
            ),
            EconomicProposal(
                payload=EconomicProposalPayload(action_type=EconomicActionType.IDLE)
            ),
            ForeignProposal(
                intent=ForeignIntent(public_intent=ForeignIntentType.IDLE, private_intent=ForeignIntentType.IDLE, reasoning="mock"),
                payload=ForeignProposalPayload(action_type=ForeignActionType.IDLE)
            )
        )
        
    agent._async_cabinet_phase = mock_cabinet
    
    # Mock presidential decision to return a dummy decree
    from geomas.agents.schemas import PresidentialDecree, DefenseDecree, EconomicDecree, ForeignDecree, PresidentialDecision
    agent._presidential_decision = MagicMock(return_value=PresidentialDecree(
        public_statement="Hello",
        defense=DefenseDecree(action=PresidentialDecision.APPROVE, reasoning="ok"),
        economy=EconomicDecree(action=PresidentialDecision.APPROVE, reasoning="ok"),
        foreign=ForeignDecree(action=PresidentialDecision.APPROVE, reasoning="ok")
    ))
    
    # Mock construct envelope to avoid more logic
    agent._construct_envelope_from_decree = MagicMock()
    
    agent.act(1, injections)
    
    expected_inj = "perform action MOVE_TROOPS with details: qty=50, to=91"
    assert actual_injections[0] == expected_inj
