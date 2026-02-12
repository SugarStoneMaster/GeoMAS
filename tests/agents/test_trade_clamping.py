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
        # Mock World
        self.world = MagicMock(spec=WorldState)
        self.world.nations = {}
        
        # Mock Client
        self.client = MagicMock(spec=LLMClient)
        
        # Mock Sender (Self)
        self.sender = MagicMock(spec=NationState)
        self.sender.name = "SenderNation"
        self.sender.total_food = 1000.0  # Limit 150
        self.sender.total_materials = 1000.0
        self.sender.total_budget = 1000.0
        self.world.nations["SENDER"] = self.sender
        
        # Mock Receiver (Target)
        self.receiver = MagicMock(spec=NationState)
        self.receiver.name = "TargetNation"
        self.receiver.total_materials = 1000.0 # Limit 150
        self.receiver.total_food = 1000.0
        self.world.nations["TARGET"] = self.receiver
        
        # Mock Agent
        self.agent = NationAgent("SENDER", self.world, self.client)
        self.agent.id = "SENDER"

    def _create_briefing_payload(self, give_type, give_amount, want_type):
        payload = EconomicProposalPayload(
            action_type=EconomicActionType.TRADE_PROPOSAL,
            target_nation_id="TARGET",
            give_type=give_type,
            give_amount=give_amount,
            want_type=want_type
        )
        intent = EconomicIntent(
            public_intent=EconomicIntentType.GROWTH,
            private_intent=EconomicIntentType.GROWTH,
            reasoning="Test"
        )
        
        # Mock Proposal Structure inside Briefing
        proposal = MagicMock(spec=EconomicProposal)
        proposal.payload = payload
        proposal.intent = intent
        
        briefing = MagicMock() # No spec to allow flexible attribute setting
        briefing.economy = proposal
        
        # Mock other ministers to avoid attribute errors if accessed
        # defense and foreign are auto-created MagicMocks
        briefing.defense.payload.moves = [] # Needed for construct_envelope default behavior
        
        return briefing

    def _create_decree(self):
        decree = MagicMock() # No spec
        decree.economy.action = PresidentialDecision.APPROVE
        decree.economy.reasoning = "Approved"
        decree.defense.action = PresidentialDecision.VETO
        decree.foreign.action = PresidentialDecision.VETO
        # Default public statement
        decree.public_statement = "Statement"
        return decree

    def test_sender_clamp(self):
        """Test clamping when sender gives too much (>15% of 1000 = 150)."""
        # Offer 500 Food (Limit 150)
        briefing = self._create_briefing_payload("food", 500.0, "materials")
        decree = self._create_decree()
        
        envelope = self.agent._construct_envelope_from_decree(1, decree, briefing)
        
        # Should be clamped to 150.0
        # 500 > 150
        self.assertAlmostEqual(envelope.economic_payload.give_amount, 150.0)
        print(f"Sender Clamp Verified: 500 -> {envelope.economic_payload.give_amount}")

    def test_receiver_receiver_clamp(self):
        """Test clamping when receiver is asked for too much."""
        # Exchange Rates: Food=1, Materials=3. Ratio 1:3 (0.33 receive per give).
        # Actually in logic: exchange_ratio = g_price / w_price = 1/3 = 0.33.
        # receive = give * 0.33.
        
        # If I give 600 Food -> 200 Materials.
        # Receiver has 1000 Materials. Limit is 150.
        # 200 > 150. So acceptable receive is 150.
        # give_limit = 150 / 0.333 = 450.
        
        self.sender.total_food = 10000.0 # Limit 1500, so we don't hit sender clamp
        
        briefing = self._create_briefing_payload("food", 600.0, "materials")
        decree = self._create_decree()
        
        envelope = self.agent._construct_envelope_from_decree(1, decree, briefing)
        
        # Should be clamped to 450.0
        self.assertAlmostEqual(envelope.economic_payload.give_amount, 450.0)
        print(f"Receiver Clamp Verified: 600 -> {envelope.economic_payload.give_amount}")

    def test_no_clamp(self):
        """Test trade within limits."""
        # Offer 100 Food -> 33.3 Materials.
        # Sender Limit 150. Receiver Limit 150. All good.
        briefing = self._create_briefing_payload("food", 100.0, "materials")
        decree = self._create_decree()
        
        envelope = self.agent._construct_envelope_from_decree(1, decree, briefing)
        
        self.assertAlmostEqual(envelope.economic_payload.give_amount, 100.0)
        print("No Clamp Verified")

if __name__ == '__main__':
    unittest.main()
