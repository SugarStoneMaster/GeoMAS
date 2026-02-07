import unittest
from unittest.mock import MagicMock, patch
import random
from geomas.simulation.engine import SimulationEngine
from geomas.agents.llm_client import LLMClient
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy
from geomas.actions.defense.schemas import DefensePayload, DefenseActionItem, DefenseActionType
from geomas.actions.common import Decision

class TestSequentialExecution(unittest.TestCase):
    def setUp(self):
        # Initialize engine with a fixed seed and enough cells for nations
        self.client = MagicMock(spec=LLMClient)
        self.sim = SimulationEngine(
            map_seed=42, 
            history_seed=99, 
            n_cells=200, 
            llm_client=self.client
        )
        # Give all nations plenty of resources to ensure actions succeed
        for nation in self.sim.world.nations.values():
            nation.total_budget = 10000
            nation.total_materials = 10000
            nation.total_energy = 10000
            nation.total_workers = 10000
            
        print(f"Generated world with {len(self.sim.world.nations)} nations.")

    def test_deterministic_shuffling(self):
        """Verify that the turn order is shuffled but deterministic across runs with same seed."""
        nation_ids = list(self.sim.agents.keys())
        self.assertGreater(len(nation_ids), 1, "Should have at least 2 nations for this test.")
        
        # Turn 1 order
        rng1 = random.Random(self.sim.history_seed + 1)
        expected_order_1 = list(nation_ids)
        rng1.shuffle(expected_order_1)
        
        # Turn 2 order
        rng2 = random.Random(self.sim.history_seed + 2)
        expected_order_2 = list(nation_ids)
        rng2.shuffle(expected_order_2)
        
        # They should be different
        self.assertNotEqual(expected_order_1, expected_order_2)

    def test_sequential_state_propagation(self):
        """Verify that Nation B sees the results of Nation A's action in the same turn."""
        nation_ids = list(self.sim.agents.keys())
        self.assertGreater(len(nation_ids), 1, "Should have at least 2 nations for this test.")
        
        # Determine current turn (will be 1 after sim.step())
        current_turn = self.sim.world.turn + 1
        
        # Determine order for this turn
        turn_rng = random.Random(self.sim.history_seed + current_turn)
        shuffled_ids = list(nation_ids)
        turn_rng.shuffle(shuffled_ids)
        
        first_nation = shuffled_ids[0]
        second_nation = shuffled_ids[1]
        
        print(f"Test Order: 1st={first_nation}, 2nd={second_nation}")
        
        # First nation will create 100 soldiers in its capital
        cap_id = self.sim.world.nations[first_nation].capital_province_id
        
        from geomas.actions.economy import EconomicPayload
        from geomas.actions.foreign import ForeignPayload
        
        mock_envelope_1 = CountryEnvelope(
            turn=current_turn,
            sender_id=first_nation,
            global_strategy=GlobalStrategy.COALITION_BUILDER,
            public_statement="Boosting defense",
            defense_payload=DefensePayload(
                decision=Decision.APPROVE,
                moves=[DefenseActionItem(
                    priority=1,
                    action_type=DefenseActionType.CREATE_UNIT,
                    parameters={"quantity": 100, "unit_type": "SOLDIER", "province_id": cap_id}
                )]
            ),
            defense_public_intent="DETERRENCE",
            defense_private_intent="DETERRENCE",
            defense_private_reasoning="None",
            economic_payload=EconomicPayload(decision=Decision.VETO, action_type=None),
            economic_public_intent="IDLE",
            economic_private_intent="IDLE",
            economic_private_reasoning="None",
            foreign_payload=ForeignPayload(decision=Decision.VETO, action_type=None),
            foreign_public_intent="IDLE",
            foreign_private_intent="IDLE",
            foreign_private_reasoning="None"
        )
        
        # Second nation will just idle
        mock_envelope_2 = CountryEnvelope(
            turn=current_turn,
            sender_id=second_nation,
            global_strategy=GlobalStrategy.COALITION_BUILDER,
            public_statement="Doing nothing",
            defense_payload=DefensePayload(decision=Decision.VETO, moves=[]),
            defense_public_intent="IDLE",
            defense_private_intent="IDLE",
            defense_private_reasoning="None",
            economic_payload=EconomicPayload(decision=Decision.VETO, action_type=None),
            economic_public_intent="IDLE",
            economic_private_intent="IDLE",
            economic_private_reasoning="None",
            foreign_payload=ForeignPayload(decision=Decision.VETO, action_type=None),
            foreign_public_intent="IDLE",
            foreign_private_intent="IDLE",
            foreign_private_reasoning="None"
        )

        captured_state = {'soldiers_at_start': self.sim.world.provinces[cap_id].soldiers}

        # Patch run_opinion_phase and run_upkeep_phase to avoid side effects with mocks
        with patch('geomas.simulation.engine.run_opinion_phase'), \
             patch('geomas.simulation.engine.run_upkeep_phase'):
            
            # Manual wrap of agent.act
            def create_mock_act(nid):
                if nid == first_nation:
                    return lambda turn: mock_envelope_1
                if nid == second_nation:
                    def act_with_capture(turn):
                        # Capture state: does Second see the 100 soldiers created by First?
                        captured_state['soldiers_seen_by_second'] = self.sim.world.provinces[cap_id].soldiers
                        return mock_envelope_2
                    return act_with_capture
                # Default empty act
                return lambda turn, nid=nid: CountryEnvelope(
                    turn=turn, sender_id=nid, global_strategy=GlobalStrategy.COALITION_BUILDER,
                    public_statement="Idle",
                    defense_payload=DefensePayload(decision=Decision.VETO, moves=[]),
                    defense_public_intent="IDLE", defense_private_intent="IDLE", defense_private_reasoning="",
                    economic_payload=EconomicPayload(decision=Decision.VETO, action_type=None),
                    economic_public_intent="IDLE", economic_private_intent="IDLE", economic_private_reasoning="",
                    foreign_payload=ForeignPayload(decision=Decision.VETO, action_type=None),
                    foreign_public_intent="IDLE", foreign_private_intent="IDLE", foreign_private_reasoning=""
                )

            for nid, agent in self.sim.agents.items():
                agent.act = create_mock_act(nid)

            # Run step
            self.sim.step()
        
        # Check engine logs for debugging
        print("Engine Logs:")
        for log in self.sim.turn_logs:
            print(f"  {log}")
            
        # Check results
        print(f"Soldiers at start: {captured_state['soldiers_at_start']}")
        print(f"Soldiers seen by {second_nation}: {captured_state.get('soldiers_seen_by_second', 'NOT CAPTURED')}")
        
        self.assertEqual(
            captured_state.get('soldiers_seen_by_second'), 
            captured_state['soldiers_at_start'] + 100,
            "Sequential execution failed: Second nation did not see updated world state."
        )

if __name__ == "__main__":
    unittest.main()
