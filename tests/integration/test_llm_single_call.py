"""
Test LLM Integration Script.

Generates prompts for a single agent call and optionally sends to LLM.
Usage:
    PYTHONPATH=. python tests/integration/test_llm_single_call.py --dry-run  # Just print prompts
    PYTHONPATH=. python tests/integration/test_llm_single_call.py             # Call LLM
"""
import argparse
import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()
from geomas.world import generate_world
from geomas.agents.context.system import DefenseSystemPrompt
from geomas.agents.context.input import DefenseInputBuilder
from geomas.agents.context.memory import ContextManager
from geomas.agents.context.tokens import TokenCounter
from geomas.agents.schemas import GlobalStrategy, DefenseProposal


def main():
    parser = argparse.ArgumentParser(description="Test LLM Integration")
    parser.add_argument("--dry-run", action="store_true", help="Only print prompts, don't call LLM")
    parser.add_argument("--model", default="azure/gpt-5-nano", help="Model to use (e.g., azure/gpt-5-nano)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧪 LLM INTEGRATION TEST")
    print("=" * 60)
    
    # Generate world
    print("\n📍 Generating world...")
    world = generate_world(seed=42, history_seed=99, n_cells=200, n_nations=4)
    
    # Initialize context manager
    cm = ContextManager()
    cm.initialize_from_world(world)
    
    # Pick first nation
    nation_id = list(world.nations.keys())[0]
    nation = world.nations[nation_id]
    strategy = GlobalStrategy.TOTAL_EXPANSIONISM
    
    print(f"✅ Testing with: {nation.name} (strategy: {strategy.value})")
    
    # Generate prompts
    print("\n📝 Generating prompts...")
    
    system_prompt = DefenseSystemPrompt.generate(
        nation_name=nation.name,
        strategy=strategy
    )
    
    input_builder = DefenseInputBuilder(world)
    user_prompt = input_builder.build(nation_id)
    
    # Add memory context
    actions = cm.get_actions_for(nation_id, domain="Defense", max_actions=5)
    if actions:
        user_prompt += "\n\n== YOUR RECENT DEFENSE ACTIONS ==\n"
        user_prompt += "\n".join(actions)
    
    # Token analysis
    counter = TokenCounter()
    system_tokens = counter.count(system_prompt)
    user_tokens = counter.count(user_prompt)
    total_tokens = system_tokens + user_tokens
    
    print("\n" + "=" * 60)
    print("📊 TOKEN ANALYSIS")
    print("=" * 60)
    print(f"System prompt: {system_tokens} tokens")
    print(f"User prompt:   {user_tokens} tokens")
    print(f"TOTAL:         {total_tokens} tokens ({total_tokens/5000*100:.0f}% of budget)")
    
    print("\n" + "=" * 60)
    print("📋 SYSTEM PROMPT")
    print("=" * 60)
    print(system_prompt)
    
    print("\n" + "=" * 60)
    print("📋 USER PROMPT")
    print("=" * 60)
    print(user_prompt)
    
    if args.dry_run:
        print("\n" + "=" * 60)
        print("🔒 DRY RUN - No LLM call made")
        print("=" * 60)
        print("To call the LLM, run without --dry-run flag")
        return
    
    # Call LLM
    print("\n" + "=" * 60)
    print("🤖 CALLING LLM...")
    print("=" * 60)
    
    try:
        from geomas.agents.llm_client import LLMClient
        
        client = LLMClient(model_name=args.model, temperature=0.2)
        
        response = client.query_agent(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=DefenseProposal,
            max_retries=2
        )
        
        print("\n✅ LLM RESPONSE:")
        print("-" * 40)
        print(f"Intent Type: {response.intent.type}")
        print(f"Reasoning: {response.intent.reasoning}")
        print(f"Urgency: {response.urgency}")
        print(f"Payload Moves: {len(response.payload.moves)} actions")
        
        if response.payload.moves:
            print("\nActions proposed:")
            for move in response.payload.moves[:3]:
                print(f"  - {move}")
                
    except Exception as e:
        print(f"\n❌ LLM CALL FAILED: {e}")
        print("\n📋 Configuration for Azure OpenAI (LiteLLM):")
        print("  export AZURE_API_KEY=your_key")
        print("  export AZURE_API_BASE=https://ciem-mlb985wq-swedencentral.cognitiveservices.azure.com")
        print("  export AZURE_API_VERSION=2024-02-01")
        print("\n  Then use: --model azure/gpt-5-nano")


if __name__ == "__main__":
    main()
