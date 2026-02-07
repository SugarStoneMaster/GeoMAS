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
    print("🤖 CALLING LLM (LiteLLM - single call)...")
    print("=" * 60)
    
    try:
        from litellm import completion
        import json
        
        # LiteLLM call - uses env vars AZURE_API_KEY, AZURE_API_BASE automatically
        # reasoning_effort controls reasoning tokens: "none", "minimal", "low", "medium", "high"
        raw_response = completion(
            model=args.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            reasoning_effort="minimal"  # Minimize reasoning tokens
        )
        
        raw_content = raw_response.choices[0].message.content
        usage = raw_response.usage
        
        # Token usage
        print("\n" + "=" * 60)
        print("📊 TOKEN USAGE")
        print("=" * 60)
        reasoning_tokens = 0
        if hasattr(usage, 'completion_tokens_details') and usage.completion_tokens_details:
            reasoning_tokens = getattr(usage.completion_tokens_details, 'reasoning_tokens', 0) or 0
        print(f"Prompt tokens:     {usage.prompt_tokens}")
        print(f"Completion tokens: {usage.completion_tokens}")
        if reasoning_tokens:
            print(f"  - Reasoning:     {reasoning_tokens}")
            print(f"  - Output:        {usage.completion_tokens - reasoning_tokens}")
        print(f"TOTAL:             {usage.total_tokens}")
        
        # Raw output
        print("\n" + "=" * 60)
        print("📄 RAW LLM OUTPUT")
        print("=" * 60)
        print(raw_content)
        
        # Parse JSON manually
        print("\n" + "=" * 60)
        print("✅ PARSED RESPONSE")
        print("=" * 60)
        
        try:
            # Find JSON in the response (might be wrapped in markdown)
            json_start = raw_content.find("{")
            json_end = raw_content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = raw_content[json_start:json_end]
                parsed = json.loads(json_str)
                print(json.dumps(parsed, indent=2))
                
                # Show key fields
                print("\n--- Summary ---")
                print(f"Threat Level: {parsed.get('threat_level', 'N/A')}")
                print(f"Summary: {parsed.get('summary', 'N/A')}")
                actions = parsed.get('recommended_actions', [])
                print(f"Actions: {len(actions)}")
                for i, action in enumerate(actions[:3], 1):
                    print(f"  {i}. {action.get('action', 'N/A')}: {action.get('reasoning', 'N/A')[:60]}...")
            else:
                print("Could not extract JSON from response")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
                
    except Exception as e:
        print(f"\n❌ LLM CALL FAILED: {e}")
        print("\n📋 Configuration for Azure OpenAI (LiteLLM):")
        print("  export AZURE_API_KEY=your_key")
        print("  export AZURE_API_BASE=https://your-endpoint.cognitiveservices.azure.com")
        print("  export AZURE_API_VERSION=2024-02-01")
        print("\n  Then use: --model azure/gpt-5-nano")


if __name__ == "__main__":
    main()
