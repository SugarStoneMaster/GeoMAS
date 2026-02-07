"""
Verification test for Simplified Token Observability.
Tests extraction of Turn, Nation, and Role from prompts.
"""
import unittest
import os
import csv
from unittest.mock import MagicMock
from geomas.simulation.engine import SimulationEngine
from geomas.agents.llm_client import LLMClient
from geomas.agents.schemas.protocol import (
    DefenseProposal, EconomicProposal, ForeignProposal, PresidentialDecree,
    DefenseIntent, DefenseIntentType, DefensePayload,
    EconomicIntent, EconomicIntentType,
    ForeignIntent, ForeignIntentType,
    DefenseDecree, EconomicDecree, ForeignDecree
)
from geomas.actions.economy import EconomicPayload
from geomas.actions.foreign import ForeignPayload
from geomas.agents.opinion import OpinionResponse
from geomas.actions.common import Decision

class TestTokenObservability(unittest.TestCase):
    def setUp(self):
        self.log_file = "logs/token_usage.csv"
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
            
    def test_token_logging_flow(self):
        """Verify that running a turn creates a CSV with token logs using real extraction logic."""
        # Use real LLMClient but mock the underlying instructor client
        client = LLMClient(model_name="mock-model")
        mock_instructor = MagicMock()
        client.client = mock_instructor
        
        def mock_completion_create(*args, **kwargs):
            response_model = kwargs.get('response_model')
            
            # Setup a mock completion object for usage
            mock_usage = MagicMock()
            mock_usage.prompt_tokens = 10
            mock_usage.completion_tokens = 25
            mock_usage.total_tokens = 35
            
            # Simulate o1/o3-mini reasoning tokens
            mock_details = MagicMock()
            mock_details.reasoning_tokens = 5
            mock_usage.completion_tokens_details = mock_details
            
            mock_raw = MagicMock()
            mock_raw.usage = mock_usage
            
            # Create a real response object to avoid validation issues in simulation
            if "DefenseProposal" in str(response_model):
                res = DefenseProposal(
                    intent=DefenseIntent(type=DefenseIntentType.DEFENSE, reasoning="mock"),
                    payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
                    urgency=5
                )
            elif "EconomicProposal" in str(response_model):
                res = EconomicProposal(
                    intent=EconomicIntent(type=EconomicIntentType.GROWTH, reasoning="mock"),
                    payload=EconomicPayload(decision=Decision.APPROVE),
                    projected_cost=0.0
                )
            elif "ForeignProposal" in str(response_model):
                res = ForeignProposal(
                    intent=ForeignIntent(type=ForeignIntentType.COOPERATION, reasoning="mock"),
                    payload=ForeignPayload(decision=Decision.APPROVE),
                    target_trust_impact=0.0
                )
            elif "PresidentialDecree" in str(response_model):
                res = PresidentialDecree(
                    defense=DefenseDecree(action=Decision.APPROVE, reasoning="mock"),
                    economy=EconomicDecree(action=Decision.APPROVE, reasoning="mock"),
                    foreign=ForeignDecree(action=Decision.APPROVE, reasoning="mock"),
                    public_statement="mock",
                    defense_public_intent=DefenseIntentType.DEFENSE,
                    defense_private_intent=DefenseIntentType.DEFENSE,
                    economic_public_intent=EconomicIntentType.GROWTH,
                    economic_private_intent=EconomicIntentType.GROWTH,
                    foreign_public_intent=ForeignIntentType.COOPERATION,
                    foreign_private_intent=ForeignIntentType.COOPERATION,
                    defense_private_reasoning="mock",
                    economic_private_reasoning="mock",
                    foreign_private_reasoning="mock"
                )
            elif "OpinionResponse" in str(response_model):
                res = OpinionResponse(multiplier_increase=1.0, multiplier_decrease=1.0, mood="NEUTRAL", reasoning="mock")
            else:
                res = MagicMock(spec=response_model)
                
            return res, mock_raw

        mock_instructor.chat.completions.create_with_completion.side_effect = mock_completion_create

        # Initialize engine
        sim = SimulationEngine(llm_client=client, n_cells=100)
        
        # Run 1 turn
        sim.step()
        
        # Close engine to flush logs
        sim.close()
        
        # Verify CSV exists
        self.assertTrue(os.path.exists(self.log_file))
        
        # Verify CSV contents
        with open(self.log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            self.assertGreater(len(rows), 0)
            
            found_roles = [row['role'] for row in rows]
            # Role names as defined in prompts (e.g. "Defense Minister", "President", "voice of the people")
            self.assertIn('Defense Minister', found_roles)
            self.assertIn('President', found_roles)
            self.assertTrue(any("voice" in role.lower() for role in found_roles))
            
            for row in rows:
                self.assertEqual(row['turn'], '1')
                self.assertNotEqual(row['nation_id'], 'unknown')
                self.assertNotEqual(row['role'], 'unknown')
                self.assertEqual(row['reasoning_tokens'], '5')

if __name__ == "__main__":
    unittest.main()
