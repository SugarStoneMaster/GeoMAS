import unittest
from unittest.mock import MagicMock
from geomas.agents.nation_agent import NationAgent
from geomas.actions.economy.schemas import EconomicActionType, EconomicProposalPayload, EconomicPayload
from geomas.agents.schemas import (
    CabinetBriefing, PresidentialDecree, PresidentialDecision, Decision, 
    CountryEnvelope, GlobalStrategy, EconomicIntent, EconomicIntentType,
    EconomicProposal
)
from geomas.schemas.world import WorldState, NationState
from geomas.actions.economy.trade import BASE_PRICES
from geomas.agents.llm_client import LLMClient

class TestTradeClamping(unittest.TestCase):
    def setUp(self):
        # Mock World with Real Objects (to allow attribute setting)
        from geomas.schemas.world import WorldState, NationState
        self.world = WorldState()
        
        self.sender = NationState(id="SENDER", name="Sender", color="#FF0000", total_food=1000.0, total_materials=1000.0, total_budget=1000.0)
        # Receiver needs enough materials to pay for 150 Food (Value 150) -> 50 Materials.
        # Receiver needs stock > 50 / 0.15 = 333 to avoid clamping.
        self.receiver = NationState(id="TARGET", name="Target", color="#0000FF", total_food=1000.0, total_materials=1000.0)
        
        self.world.nations["SENDER"] = self.sender
        self.world.nations["TARGET"] = self.receiver
        self.world.trust_matrix = {"SENDER": {"TARGET": 50}} # Base trust
        
        # Real Engine
        from geomas.actions.engine import ActionEngine
        self.engine = ActionEngine(self.world)

    def test_sender_clamp(self):
        """Test clamping when sender gives too much (>15% of 1000 = 150)."""
        from geomas.actions.economy.handler import execute_economic
        
        # Payload: Give 500 Food (Limit 150)
        payload = EconomicPayload(
            action_type=EconomicActionType.TRADE_PROPOSAL,
            target_nation_id="TARGET",
            give_type="food",
            give_amount=500.0,
            want_type="materials"
        )
        
        execute_economic(self.engine, "SENDER", payload)
        
        # Check output details for clamped amount
        self.assertEqual(payload.execution_outcome.status, "SUCCESS")
        self.assertAlmostEqual(payload.execution_outcome.details["give_amount"], 150.0)
        
        # Check log
        clamped_log = next((l for l in self.engine.logs if "Clamped" in l), None)
        self.assertIsNotNone(clamped_log)
        print(f"Verified Log: {clamped_log}")

    def test_no_clamp(self):
        """Test trade within limits (100 < 150)."""
        from geomas.actions.economy.handler import execute_economic
        
        payload = EconomicPayload(
            action_type=EconomicActionType.TRADE_PROPOSAL,
            target_nation_id="TARGET",
            give_type="food",
            give_amount=100.0,
            want_type="materials"
        )
        
        execute_economic(self.engine, "SENDER", payload)
        
        self.assertEqual(payload.execution_outcome.status, "SUCCESS")
        self.assertAlmostEqual(payload.execution_outcome.details["give_amount"], 100.0)
        
        # Ensure NO clamp log
        clamped_log = next((l for l in self.engine.logs if "Clamped" in l), None)
        self.assertIsNone(clamped_log)

if __name__ == '__main__':
    unittest.main()
