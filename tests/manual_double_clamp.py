
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from geomas.actions.engine import ActionEngine
from geomas.world.generation.generator import MapGenerator
from geomas.actions.economy.schemas import EconomicPayload, EconomicActionType
from geomas.actions.economy.handler import execute_economic
from geomas.agents.context.input.economy import EconomyInputBuilder

def test_double_clamping():
    print("--- 🛠️ TESTING DOUBLE CLAMPING (RECEIVER PROTECTION) ---")
    
    # 1. Setup World
    generator = MapGenerator(seed=42, n_cells=100, n_nations=2, relaxation_steps=0)
    world = generator.generate(history_seed=99)
    engine = ActionEngine(world)
    
    n_ids = list(world.nations.keys())
    sender = n_ids[0]
    receiver = n_ids[1]
    
    # 2. Setup Resources 
    # Sender has LOTS of Food (so they can offer 500 easily)
    world.nations[sender].total_food = 10000.0 
    # Receiver has LITTLE Materials (so they can't afford big trade)
    world.nations[receiver].total_materials = 1000.0 
    
    print(f"Sender Food: {world.nations[sender].total_food}")
    print(f"Receiver Materials: {world.nations[receiver].total_materials}")
    
    # Max Receiver Pay = 150 Materials.
    # Price Ratio (Default): Food=1, Materials=3.
    # 1 Material = 3 Food.
    # So Receiver can pay max 150 Materials, which buys 450 Food.
    
    # 3. Attempt Oversized Trade
    # Offer 1000 Food (Value 1000). 
    # Requires 333 Materials from Receiver.
    # 333 > 150 (Clamp Limit).
    amount = 1000.0
    print(f"Attempting Export: {amount} Food -> Expected 333 Materials")
    
    payload = EconomicPayload(
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id=receiver,
        give_type="food",
        give_amount=amount,
        want_type="materials"
    )
    
    # Execute
    print("\n--- EXECUTION ---")
    execute_economic(engine, sender, payload)
    
    # Verify Logs
    # Expect "Clamped by RECEIVER"
    receiver_clamp_log = next((l for l in engine.logs if "RECEIVER limit" in l), None)
    
    if receiver_clamp_log:
        print(f"✅ FOUND RECEIVER CLAMP LOG: {receiver_clamp_log}")
        # Extract numbers to verify scaling
        # Should be ~450 Food <-> ~150 Materials
    else:
        print("❌ NO RECEIVER CLAMP LOG FOUND!")
        for l in engine.logs: print(l)

    # 4. Verify Context Feedback
    print("\n--- CONTEXT GENERATION ---")
    builder = EconomyInputBuilder(world)
    recent_actions = [receiver_clamp_log] if receiver_clamp_log else []
    
    prompt = builder.build(sender, turn=2, recent_actions=recent_actions)
    
    if "FEEDBACK FROM PREVIOUS TURN" in prompt:
         print("✅ FOUND FEEDBACK WARNING IN PROMPT.")
    else:
         print("❌ NO FEEDBACK WARNING FOUND.")

if __name__ == "__main__":
    test_double_clamping()
