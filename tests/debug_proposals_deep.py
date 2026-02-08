
import pickle
import json
from geomas.world import generate_world
from geomas.agents.ministers import ForeignMinister
from geomas.agents.llm_client import LLMClient
from geomas.actions import ActionEngine
from geomas.actions.foreign import ForeignPayload, ForeignActionType, execute_foreign
from geomas.agents.schemas import GlobalStrategy, ForeignProposal, ForeignIntent, ForeignIntentType
from geomas.agents.context.input import ForeignInputBuilder

class MockLLM(LLMClient):
    def query_agent(self, system, user, schema):
        # Return a dummy proposal
        return ForeignProposal(
            intent=ForeignIntent(
                public_intent=ForeignIntentType.IDLE,
                private_intent=ForeignIntentType.IDLE,
                reasoning="Idle"
            ),
            payload=ForeignPayload(target_nation_id="NONE", decision="PENDING")
        )

def test_prompt_visibility():
    print("--- TEST 1: PROMPT VISIBILITY ---")
    world = generate_world(seed=42, n_nations=3, n_cells=100)
    
    n1_id = list(world.nations.keys())[0]
    n2_id = list(world.nations.keys())[1]
    
    # Manually inject proposal
    world.nations[n1_id].pending_proposals.append({
        "type": "ALLIANCE",
        "from": n2_id,
        "turn": 1,
        "message": "Manual Injection"
    })
    
    # Build prompt
    builder = ForeignInputBuilder(world)
    prompt = builder.build(n1_id, turn=2)
    
    print(f"Checking prompt for {n1_id}...")
    if "ALLIANCE proposal from" in prompt and "Manual Injection" in prompt:
        print("✅ SUCCESS: Proposal visible in prompt")
    else:
        print("❌ FAILURE: Proposal NOT visible in prompt")
        print("Prompt snippet:", prompt[:500])

def test_action_persistence():
    print("\n--- TEST 2: ACTION PERSISTENCE ---")
    world = generate_world(seed=42, n_nations=3, n_cells=100)
    engine = ActionEngine(world)
    
    n1_id = list(world.nations.keys())[0]
    n2_id = list(world.nations.keys())[1]
    
    # N1 proposes to N2
    payload = ForeignPayload(
        action_type=ForeignActionType.PROPOSE_ALLIANCE,
        target_nation_id=n2_id,
        message="Persistence Test"
    )
    
    # Ensure trust
    world.trust_matrix.setdefault(n1_id, {})[n2_id] = 80.0
    
    execute_foreign(engine, n1_id, payload)
    
    # Check N2 state
    n2 = world.nations[n2_id]
    if len(n2.pending_proposals) == 1:
        print("✅ SUCCESS: Proposal persisted in memory")
    else:
        print("❌ FAILURE: Proposal NOT in memory after execution")

    # Verify ID match
    if id(engine.world) == id(world):
        print("✅ SUCCESS: Engine world and Local world are same object")
    else:
        print("❌ FAILURE: Engine world is DIFFERENT object")

    if id(engine.world.nations[n2_id]) == id(n2):
        print("✅ SUCCESS: Nation object is same")
    else:
        print("❌ FAILURE: Nation object is DIFFERENT")

def test_serialization_survival():
    print("\n--- TEST 3: SERIALIZATION SURVIVAL ---")
    world = generate_world(seed=42, n_nations=3, n_cells=100)
    n1_id = list(world.nations.keys())[0]
    
    # Inject
    world.nations[n1_id].pending_proposals.append({
        "type": "TEST",
        "from": "UNKNOWN",
        "turn": 1
    })
    
    # Pickle and Unpickle (simulating Streamlit session state or DB logic)
    dumped = pickle.dumps(world)
    loaded_world = pickle.loads(dumped)
    
    n1_loaded = loaded_world.nations[n1_id]
    
    if len(n1_loaded.pending_proposals) == 1:
        print("✅ SUCCESS: Pending proposals survived Pickle")
    else:
        print("❌ FAILURE: Pending proposals LOST during Pickle")
        
    # JSON Dump (Pydantic)
    try:
        json_str = world.nations[n1_id].model_dump_json()
        if "pending_proposals" in json_str and "TEST" in json_str:
            print("✅ SUCCESS: Pending proposals in JSON dump")
        else:
            print("❌ FAILURE: Pending proposals missing from JSON dump")
            print(json_str)
    except Exception as e:
        print(f"❌ FAILURE: JSON Dump raised error: {e}")

if __name__ == "__main__":
    test_prompt_visibility()
    test_action_persistence()
    test_serialization_survival()
