
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from geomas.schemas.world import WorldState, ProvinceState, NationState, TerrainType
from geomas.agents.context.events.context_manager import ContextManager
from geomas.agents.context.input.economy import EconomyInputBuilder
from geomas.agents.context.input.defense import DefenseInputBuilder
from geomas.actions.economy.schemas import EconomicPayload, EconomicActionType
from geomas.actions.defense.schemas import DefensePayload, DefenseActionItem, DefenseActionType, UnitType
from geomas.actions.common import ExecutionOutcome, Decision
from geomas.agents.schemas.protocol import CountryEnvelope

def test_feedback_loop():
    # 1. Setup World
    p1 = ProvinceState(id=1, owner_id="N1", terrain=TerrainType.LAND, coordinates=(0, 0))
    p2 = ProvinceState(id=2, owner_id="N2", terrain=TerrainType.LAND, soldiers=100, coordinates=(1, 1))
    
    n1 = NationState(id="N1", name="Nation 1", color="blue", province_ids=[1], total_food=100)
    n2 = NationState(id="N2", name="Nation 2", color="red", province_ids=[2], total_food=1000)
    
    world = WorldState(
        turn=1,
        provinces={1: p1, 2: p2},
        nations={"N1": n1, "N2": n2},
        trust_matrix={"N1": {"N2": 10.0}}, # Low trust
        relationship_matrix={"N1": {"N2": "PEACE"}}
    )
    
    cm = ContextManager()
    cm.initialize_from_world(world)
    
    # 2. Simulate TURN 1 Actions
    # Case A: Economy Trade Rejected (Trust too low)
    eco_payload = EconomicPayload(
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id="N2",
        give_type="food",
        give_amount=50,
        want_type="energy",
        decision=Decision.APPROVE
    )
    eco_payload.execution_outcome.status = "REJECTED"
    eco_payload.execution_outcome.reason = "Trust too low (10 < 40)"
    
    # Case B: Defense Attack (Combat Details)
    def_item = DefenseActionItem(
        action_type=DefenseActionType.MOVE_TROOPS,
        unit_type=UnitType.SOLDIER,
        quantity=50,
        source_province_id=1,
        target_province_id=2,
        target_nation_id="N2",
        priority=1
    )
    def_item.execution_outcome.status = "FAILED"
    def_item.execution_outcome.reason = "Defender wins! 50 attackers destroyed."
    def_item.execution_outcome.details = {
        "attacker_wins": False,
        "attacker_losses": 50,
        "defender_losses": 0
    }
    def_payload = DefensePayload(moves=[def_item], decision=Decision.APPROVE)
    
    from geomas.actions.foreign.schemas import ForeignPayload
    
    envelope = CountryEnvelope.model_construct(
        sender_id="N1",
        turn=1,
        economic_payload=eco_payload,
        defense_payload=def_payload,
        foreign_payload=ForeignPayload.model_construct(),
        global_strategy=None,
        public_statement="Testing",
        defense_public_intent=None,
        defense_private_intent=None,
        defense_private_reasoning="N/A",
        economic_public_intent=None,
        economic_private_intent=None,
        economic_private_reasoning="N/A",
        foreign_public_intent=None,
        foreign_private_intent=None,
        foreign_private_reasoning="N/A"
    )
    
    # 3. Update ContextManager after Turn 1
    # Move world to turn 2
    world.turn = 2
    cm.update_after_turn(turn=1, envelopes=[envelope], world=world)
    
    # 4. Verify Turn 2 Context
    # A. Economy Prompt
    eco_builder = EconomyInputBuilder(world)
    eco_prompt = eco_builder.build("N1", 2, context_manager=cm)
    
    print("\n--- ECONOMY PROMPT Snippet ---")
    if "REJECTED (Trust too low (10 < 40))" in eco_prompt:
        print("SUCCESS: Found rejection reason in Economy history.")
    else:
        print("FAILURE: Rejection reason missing in Economy history.")
        # print(eco_prompt)
        
    # B. Defense Prompt
    def_builder = DefenseInputBuilder(world)
    def_prompt = def_builder.build("N1", 2, context_manager=cm)
    
    print("\n--- DEFENSE PROMPT Snippet ---")
    if "Battle Result: Defender won!" in def_prompt:
        print("SUCCESS: Found combat result in Defense events.")
    else:
        print("FAILURE: Combat result missing in Defense events.")
        
    if "FAILED (Defender wins! 50 attackers destroyed.)" in def_prompt:
        print("SUCCESS: Found detailed failure reason in Defense history.")
    else:
        print("FAILURE: Detailed failure reason missing in Defense history.")

if __name__ == "__main__":
    test_feedback_loop()
