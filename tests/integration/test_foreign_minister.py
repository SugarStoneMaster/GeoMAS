
"""
Test Foreign Minister Agent Integration.

Standalone script to test the Foreign Minister agent's prompt generation and LLM response.
Can be run as a CLI script or imported by other tools (like agent_debugger.py).

Usage:
    python tests/integration/test_foreign_minister.py --dry-run
    python tests/integration/test_foreign_minister.py --model gpt-4o-mini
"""
import argparse
import sys
import os
import json
from typing import Tuple, Optional
from dotenv import load_dotenv

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Load .env file (assuming it's in project root)
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env")))

from geomas.world import generate_world
from geomas.agents.llm_client import LLMClient, LLMUsage
from geomas.agents.ministers import ForeignMinister
from geomas.agents.context.system import ForeignSystemPrompt
from geomas.agents.context.input import ForeignInputBuilder
from geomas.agents.schemas import GlobalStrategy, ForeignProposal

# --- REUSABLE FUNCTIONS ---

def get_test_world(seed: int = 39, n_nations: int = 10):
    """Generate a consistent world for testing."""
    return generate_world(seed=seed, n_cells=1500, n_nations=n_nations)

def get_foreign_prompts(
    world, 
    nation_id: str, 
    strategy: GlobalStrategy,
    turn: int = 1,
    target_relationships: Optional[dict] = None
) -> Tuple[str, str]:
    """
    Generate System and User prompts for the Foreign Minister.
    
    Args:
        world: WorldState
        nation_id: ID of the nation
        strategy: GlobalStrategy to use
        target_relationships: Dict of {target_id: 'WAR'|'PEACE'|...} to override context
    
    Returns:
        (system_prompt, user_prompt)
    """
    # Override relationships if provided
    if target_relationships:
        if nation_id not in world.relationship_matrix:
            world.relationship_matrix[nation_id] = {}
        for tid, rel in target_relationships.items():
            world.relationship_matrix[nation_id][tid] = rel

    # 1. System Prompt
    system_prompt = ForeignSystemPrompt.generate(
        nation_name=world.nations[nation_id].name,
        strategy=strategy
    )
    
    # 2. User Prompt
    input_builder = ForeignInputBuilder(world)
    user_prompt = input_builder.build(nation_id, turn=turn)
    
    # Mock/Add memory context logic if needed (similar to Agent logic)
    # The actual agent does this internally, but for prompt inspection we reconstruct it.
    # We can add a placeholder or verify what the builder returns.
    
    return system_prompt, user_prompt

def execute_foreign_agent(
    world, 
    nation_id: str, 
    strategy: GlobalStrategy, 
    turn: int = 1,
    model_name: str = "azure/gpt-5-nano",
    temperature: float = 0.7
) -> Tuple[ForeignProposal, Optional[LLMUsage]]:
    """
    Execute the full ForeignMinister agent pipeline.
    
    Returns:
        ForeignProposal object (Pydantic model)
    """
    client = LLMClient(model_name=model_name, temperature=temperature)
    minister = ForeignMinister(nation_id, world, client)
    
    proposal = minister.propose(strategy, turn=turn)
    return proposal, client.last_usage


# --- CLI MAIN ---

def main():
    parser = argparse.ArgumentParser(description="Test Foreign Minister Agent")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts only")
    parser.add_argument("--model", default="azure/gpt-5-nano", help="LLM Model name")
    parser.add_argument("--seed", type=int, default=42, help="World seed")
    parser.add_argument("--strategy", default="COALITION_BUILDER", help="Global Strategy to test")
    parser.add_argument("--turn", type=int, default=1, help="Turn number")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🌍 FOREIGN MINISTER INTEGRATION TEST")
    print("=" * 60)
    
    # Setup
    world = get_test_world(seed=args.seed)
    nation_id = list(world.nations.keys())[0]
    try:
        strategy_enum = GlobalStrategy(args.strategy)
    except ValueError:
        print(f"❌ Invalid strategy: {args.strategy}")
        return

    print(f"Testing Nation: {nation_id} ({world.nations[nation_id].name})")
    print(f"Strategy: {strategy_enum.value}")
    
    # Generate Prompts
    sys_p, user_p = get_foreign_prompts(world, nation_id, strategy_enum, turn=args.turn)
    
    print("\n" + "-" * 60)
    print("📋 SYSTEM PROMPT PREVIEW")
    print("-" * 60)
    print(sys_p[:300] + "...\n(truncated)")
    
    print("\n" + "-" * 60)
    print("📋 USER PROMPT PREVIEW")
    print("-" * 60)
    print(user_p)
    
    if args.dry_run:
        print("\n🔒 DRY RUN: Skipping LLM call.")
        return

    # Execute
    print("\n" + "=" * 60)
    print(f"🤖 EXECUTING AGENT ({args.model})...")
    print("=" * 60)
    
    try:
        result, usage = execute_foreign_agent(world, nation_id, strategy_enum, turn=args.turn, model_name=args.model)
        
        print("\n✅ AGENT RESPONSE RECEIVED")
        if usage:
            print(f"{usage}")
        print("-" * 60)
        print(f"Intent: {result.intent.type.value}")
        print(f"Reasoning: {result.intent.reasoning}")
        print(f"Trust Impact: {result.target_trust_impact}")
        
        if result.payload.action_type:
            print(f"Action: {result.payload.action_type.value}")
            if result.payload.diplomatic_message_type:
                print(f"Message Type: {result.payload.diplomatic_message_type.value}")
            if result.payload.proposal_ref_type:
                print(f"Proposal Ref: {result.payload.proposal_ref_type}")
        else:
            print("Action: None (Idle)")
            
        print("-" * 60)
        print("Raw Payload Decision:", result.payload.decision.value) # Expect 'Decision.APPROVE' usually in mock/test
        
    except Exception as e:
        print(f"\n❌ EXECUTION FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
