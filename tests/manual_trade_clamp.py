
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from geomas.actions.engine import ActionEngine
from geomas.world.generation.generator import MapGenerator
from geomas.actions.economy.schemas import EconomicPayload, EconomicActionType
from geomas.agents.context.input.economy import EconomyInputBuilder
from geomas.actions.economy.handler import execute_economic

def test_trade_clamping():
    print("--- 🛠️ TESTING TRADE CLAMPING ---")
    
    # 1. Setup World
    generator = MapGenerator(seed=42, n_cells=100, n_nations=2, relaxation_steps=0)
    world = generator.generate(history_seed=99)
    engine = ActionEngine(world)
    
    n_ids = list(world.nations.keys())
    sender = n_ids[0]
    receiver = n_ids[1]
    
    # 2. Setup Resources (Ensure high enough to trigger visible clamp)
    nation = world.nations[sender]
    nation.total_food = 1000.0
    
    print(f"Nation {sender} Food Stock: {nation.total_food}")
    max_export = nation.total_food * 0.15
    print(f"Expected Max Export (15%): {max_export}")
    
    # 3. Attempt Oversized Trade (50% of stock)
    amount = 500.0
    print(f"Attempting Export: {amount}")
    
    payload = EconomicPayload(
        action_type=EconomicActionType.TRADE_PROPOSAL,
        target_nation_id=receiver,
        give_type="food",
        give_amount=amount,
        want_type="budget"
    )
    
    
    # Execute
    
    # Note: Import at top level to avoid scope issues in REPL/Script
    # from geomas.actions.economy.handler import execute_economic (Already imported at top if I edit it)
    print("\n--- EXECUTION ---")
    execute_economic(engine, sender, payload)
    
    # Verify Logs
    clamped_log = next((l for l in engine.logs if "Clamped" in l), None)
    if clamped_log:
        print(f"✅ FOUND CLAMP LOG: {clamped_log}")
    else:
        print("❌ NO CLAMP LOG FOUND!")
        
    # 4. Verify Context Feedback
    print("\n--- CONTEXT GENERATION ---")
    builder = EconomyInputBuilder(world)
    # Simulate agent memory of recent actions
    recent_actions = [clamped_log] if clamped_log else []
    
    prompt = builder.build(sender, turn=2, recent_actions=recent_actions)
    
    if "FEEDBACK FROM PREVIOUS TURN" in prompt and "AUTOMATICALLY REDUCED" in prompt:
         print("✅ FOUND FEEDBACK WARNING IN PROMPT.")
         print("-" * 20)
         # Extract just the warning part
         print(prompt.split("## TURN 2")[1].split("## 💰 TREASURY")[0].strip())
         print("-" * 20)
    else:
         print("❌ NO FEEDBACK WARNING FOUND IN PROMPT.")
         print(prompt[:500])

if __name__ == "__main__":
    test_trade_clamping()
