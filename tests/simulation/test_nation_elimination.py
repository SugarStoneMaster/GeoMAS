"""
Verification test for Nation Elimination Logic.
"""

import os
import pytest
from unittest.mock import MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.schemas.world import NationState, ProvinceState, TerrainType
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy, DefenseIntentType, ForeignIntentType
from geomas.actions.defense import DefensePayload
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload
from geomas.agents.llm_client import LLMClient

class TestNationElimination:
    """Tests that annexed nations are correctly eliminated from the simulation."""

    def setup_method(self):
        self._old_val = os.environ.get("PUBLIC_OPINION_ENABLED", "true")
        os.environ["PUBLIC_OPINION_ENABLED"] = "false"

    def teardown_method(self):
        os.environ["PUBLIC_OPINION_ENABLED"] = self._old_val

    def test_nation_becomes_inactive_when_all_provinces_lost(self):
        """Verify _conquer_province sets is_active=False on last province loss."""
        # Setup using SimulationEngine with enough cells for 2 nations
        sim = SimulationEngine(n_nations=2, n_cells=50)
        world = sim.world
        engine = sim.engine
        
        nation_ids = list(world.nations.keys())
        victim_id = nation_ids[0]
        conqueror_id = nation_ids[1]
        
        victim = world.nations[victim_id]
        
        # Manually clear victim's provinces except one
        victim_province_ids = list(victim.province_ids)
        last_prov_id = victim_province_ids[0]
        
        # Transfer all but the last one
        from geomas.actions.defense.combat import _conquer_province
        for p_id in victim_province_ids[1:]:
            _conquer_province(world, conqueror_id, world.provinces[p_id])
            
        assert victim.is_active is True
        assert len(victim.province_ids) == 1
        
        # Conquer the last province
        from geomas.actions.engine import ActionEngine
        engine = MagicMock(spec=ActionEngine)
        engine.context_manager = MagicMock()
        engine.world = world
        
        _conquer_province(world, conqueror_id, world.provinces[last_prov_id], engine=engine)
        
        assert len(victim.province_ids) == 0
        assert victim.is_active is False
        
        # Check structured event logging
        engine.context_manager.log_nation_fallen.assert_called_with(
            turn=world.turn,
            victim_id=victim_id,
            victim_name=victim.name,
            conqueror_id=conqueror_id,
            conqueror_name=world.nations[conqueror_id].name
        )
        
        # Check global event (fallback/news feed)
        assert any("NATION FALLEN" in str(e) and victim_id in str(e) for e in world.global_events)

    def test_simulation_skips_inactive_nations(self):
        """Verify SimulationEngine.step skips agents of inactive nations."""
        # Setup with mocked LLM to avoid real calls
        client = MagicMock(spec=LLMClient)
        sim = SimulationEngine(n_nations=3, n_cells=50, llm_client=client)
        world = sim.world
        
        nation_ids = list(world.nations.keys())
        dead_id = nation_ids[0]
        active_ids = nation_ids[1:]
        
        # Kill one nation
        world.nations[dead_id].province_ids = []
        world.nations[dead_id].is_active = False
        
        # Mock agents to track calls
        for nid in nation_ids:
             mock_envelope = CountryEnvelope(
                 turn=1, sender_id=nid, global_strategy=GlobalStrategy.COALITION_BUILDER,
                 public_statement="IDLE",
                 defense_payload=DefensePayload(decision="VETO", moves=[]),
                 defense_public_intent=DefenseIntentType.IDLE,
                 defense_private_intent=DefenseIntentType.IDLE,
                 defense_private_reasoning="IDLE",
                 economic_payload=EconomicPayload(decision="VETO", action_type=None),
                 foreign_payload=ForeignPayload(decision="VETO", action_type=None),
                 foreign_public_intent=ForeignIntentType.IDLE,
                 foreign_private_intent=ForeignIntentType.IDLE,
                 foreign_private_reasoning="IDLE"
             )
             sim.agents[nid].act = MagicMock(return_value=mock_envelope)
             
        # Run step
        sim.step()
        
        # Verify calls
        sim.agents[dead_id].act.assert_not_called()
        for nid in active_ids:
            sim.agents[nid].act.assert_called()

    def test_phases_skip_inactive_nations(self):
        """Verify Upkeep and Opinion phases skip inactive nations."""
        from geomas.simulation.phases import run_upkeep_phase, run_opinion_phase
        
        sim = SimulationEngine(n_nations=2, n_cells=50)
        world = sim.world
        nation_ids = list(world.nations.keys())
        dead_id = nation_ids[0]
        
        # Kill one nation
        world.nations[dead_id].province_ids = []
        world.nations[dead_id].is_active = False
        world.nations[dead_id].total_budget = 1000.0
        
        # Run Upkeep
        logs = []
        run_upkeep_phase(world, logs)
        
        # Budget should not have changed for dead nation (no upkeep/consumption)
        assert world.nations[dead_id].total_budget == 1000.0
        
        # Run Opinion
        # Mock opinion agent
        opinion_agent = MagicMock()
        run_opinion_phase(world, logs, {dead_id: opinion_agent}, [], turn=1)
        
        # React should not be called
        opinion_agent.react.assert_not_called()
