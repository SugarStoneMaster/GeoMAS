"""
Simulation Engine.

The Main Loop. Orchestrates the flow of time, agent decisions, and world updates.
"""

import random
from typing import Dict, List, Optional
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy
from geomas.world import generate_world
from geomas.actions import ActionEngine
from geomas.actions.foreign import clear_expired_proposals
from geomas.agents.nation_agent import NationAgent
from geomas.agents.llm_client import LLMClient
from geomas.simulation.phases import run_upkeep_phase, run_opinion_phase
from geomas.db import SimulationDB, TurnCache
from geomas.db.serialization import serialize_world_snapshot, serialize_envelope
from geomas.analysis import DeceptionAnalyzer, CoherenceAnalyzer
from geomas.analysis.token_logger import token_logger
from geomas.agents.context.memory import ContextManager
from geomas.agents.opinion import OpinionAgent


class SimulationEngine:
    """
    The Main Loop. Orchestrates the flow of time, agent decisions, and world updates.
    
    Features:
    - Optional persistence via DuckDB when db_path is provided
    - In-memory cache of recent turns for fast context access
    """

    def __init__(
        self, 
        map_seed: int = 42, 
        history_seed: int = 99, 
        n_cells: int = 1500,
        n_nations: int = 10,  # Added configurable n_nations
        llm_client: LLMClient = None,
        db_path: Optional[str] = None,
        cache_size: int = 20
    ):
        """
        Initialize the simulation engine.
        
        Args:
            map_seed: Seed for world map generation
            history_seed: Seed for historical events
            n_cells: Number of provinces
            n_nations: Number of nations (4-10)
            llm_client: Optional LLM client for agent decisions
            db_path: Optional path to DuckDB file for persistence
            cache_size: Number of recent turns to keep in memory (default 20)
        """
        self.map_seed = map_seed
        self.history_seed = history_seed
        self.n_cells = n_cells
        self.n_nations = n_nations
        
        # 1. Initialize World
        self.world = generate_world(
            seed=map_seed, 
            history_seed=history_seed, 
            n_cells=n_cells,
            n_nations=n_nations
        )
        
        # 2. Initialize Engine
        self.engine = ActionEngine(self.world)
        
        # 3. Initialize In-Memory Cache
        self.cache = TurnCache(max_turns=cache_size)
        
        # 4. Initialize Context Manager (for LLM agent memory)
        self.context_manager = ContextManager()
        self.context_manager.initialize_from_world(self.world)
        
        # 5. Initialize Agents (needs context_manager)
        self.agents: Dict[str, NationAgent] = {}
        self.client = llm_client or LLMClient() 
        self._init_agents()
        
        # Simulation State
        self.turn_logs: List[str] = []
        # Store full envelopes for rich history visualization
        # List of turns, where each turn is a list of envelopes
        self.history: List[List[CountryEnvelope]] = []
        
        # 6. Initialize Opinion Agents (post-execution feedback)
        self.opinion_agents: Dict[str, OpinionAgent] = {}
        self._init_opinion_agents()
        
        # 7. Initialize Database (optional)
        self.db: Optional[SimulationDB] = None
        if db_path:
            self._init_db(db_path)

    def _init_db(self, db_path: str) -> None:
        """Initialize database and save initial snapshot (turn 0)."""
        self.db = SimulationDB(db_path)
        self.db.initialize(
            genesis_seed=self.map_seed,
            simulation_seed=self.history_seed,
            n_cells=self.n_cells
        )
        
        # Save initial world state (turn 1 - Genesis)
        snapshot = serialize_world_snapshot(self.world)
        self.db.save_snapshot(
            turn=1,
            **snapshot
        )
        
        # Also cache turn 1
        self.cache.add_turn(
            turn=1,
            world_state=self.world,
            envelopes=[],
            behaviors={}
        )

    def _init_agents(self):
        """Creates a NationAgent for each nation in the world."""
        # Deterministic strategy assignment using map_seed
        rng = random.Random(self.map_seed)
        strategies = list(GlobalStrategy)
        
        for nation_id in self.world.nations:
            strategy = rng.choice(strategies)
            print(f"[INIT] {nation_id} Strategy: {strategy.value}")
            
            self.agents[nation_id] = NationAgent(
                nation_id=nation_id,
                world=self.world,
                llm_client=self.client,
                global_strategy=strategy,
                context_manager=self.context_manager
            )
    
    def _init_opinion_agents(self):
        """Creates an OpinionAgent for each nation."""
        for nation_id, nation in self.world.nations.items():
            # Get cultural traits from nation if available, else empty list
            traits = getattr(nation, 'cultural_traits', []) or []
            
            self.opinion_agents[nation_id] = OpinionAgent(
                nation_id=nation_id,
                nation_name=nation.name,
                cultural_traits=traits,
                llm_client=self.client,
                world=self.world
            )

    def _calculate_behaviors(
        self, 
        envelopes: List[CountryEnvelope]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate behavior metrics for all envelopes."""
        behaviors = {}
        
        for envelope in envelopes:
            detailed = DeceptionAnalyzer.calculate_detailed_score(envelope)
            coherence = CoherenceAnalyzer.calculate_score(
                envelope.global_strategy,
                envelope.defense_private_intent,
                envelope.economic_private_intent,
                envelope.foreign_private_intent
            )
            
            behaviors[envelope.sender_id] = {
                "deception_total": detailed["total"],
                "deception_defense": detailed["defense"],
                "deception_economic": detailed["economic"],
                "deception_foreign": detailed["foreign"],
                "coherence_score": coherence,
                "global_strategy": envelope.global_strategy.value
            }
        
        return behaviors

    def _persist_envelopes(self, turn: int, envelopes: List[CountryEnvelope]) -> None:
        """Save envelopes and behaviors for a turn."""
        if self.db is None: return
        
        for envelope in envelopes:
            self.db.save_envelope(turn=turn, nation_id=envelope.sender_id, envelope_json=serialize_envelope(envelope))
            
            detailed = DeceptionAnalyzer.calculate_detailed_score(envelope)
            coherence = CoherenceAnalyzer.calculate_score(
                envelope.global_strategy,
                envelope.defense_private_intent,
                envelope.economic_private_intent,
                envelope.foreign_private_intent
            )
            self.db.save_behavior(
                turn=turn, nation_id=envelope.sender_id,
                deception_total=detailed["total"], deception_defense=detailed["defense"],
                deception_economic=detailed["economic"], deception_foreign=detailed["foreign"],
                coherence_score=coherence, global_strategy=envelope.global_strategy.value
            )

    def _persist_snapshot(self, turn: int) -> None:
        """Save world snapshot for a turn."""
        if self.db is None: return
        snapshot = serialize_world_snapshot(self.world)
        self.db.save_snapshot(turn=turn, **snapshot)

    def _cache_turn(self, turn: int, envelopes: List[CountryEnvelope]) -> None:
        """Add turn data to in-memory cache."""
        behaviors = self._calculate_behaviors(envelopes)
        self.cache.add_turn(
            turn=turn,
            world_state=self.world,
            envelopes=envelopes,
            behaviors=behaviors
        )

    def step(self):
        """Executes one full turn of the simulation."""
        
        current_turn = self.world.turn
        
        print(f"--- STARTING TURN {current_turn} ---")
        self.turn_logs.append(f"--- TURN {current_turn} ---")
        
        # Local RNG for turn determinism (shuffle order)
        turn_rng = random.Random(self.history_seed + current_turn)
        
        # 0. UPKEEP PHASE (resources, consumption, crisis)
        run_upkeep_phase(self.world, self.turn_logs)
        
        # 0b. DIPLOMACY PHASE (Clear expired proposals)
        # Verify proposals from T-2 are removed before T start
        clear_expired_proposals(self.world)
        
        
        # 1. & 2. COMBINED SEQUENTIAL PHASE (Decision + Execution per Nation)
        # Shuffle nation IDs to ensure fairness in turn order
        nation_ids = list(self.agents.keys())
        turn_rng.shuffle(nation_ids)
        
        turn_envelopes: List[CountryEnvelope] = []
        for nation_id in nation_ids:
            agent = self.agents[nation_id]
            print(f"Agent {nation_id} is thinking and acting...")
            try:
                # 1. Decision: Agent perceives the CURRENT world state
                envelope = agent.act(current_turn)
                turn_envelopes.append(envelope)
                
                # 2. Execution: Physical world changes are applied IMMEDIATELY
                # Subsequent agents in the same turn will "see" these changes in their world view
                logs = self.engine.execute_envelope(envelope)
                self.turn_logs.extend(logs)
            except Exception as e:
                print(f"Error processing agent {nation_id}: {e}")
                self.turn_logs.append(f"[SYSTEM] Critical error processing {nation_id}: {e}")
        
        # Store envelopes in history
        self.history.append(turn_envelopes)
        
        # 3. CACHE PHASE (See end of step for implementation)
        # self._cache_turn(current_turn, turn_envelopes)
        
        # 4. CONTEXT PHASE (Update agent memory)
        self.context_manager.update_after_turn(current_turn, turn_envelopes, self.world)
        
        # 5. OPINION PHASE (Population reaction - post execution)
        run_opinion_phase(
            self.world,
            self.turn_logs,
            self.opinion_agents,
            turn_envelopes,
            turn=current_turn
        )
        
        # 6. PERSIST PHASE (Database)
        # 6. PERSIST PHASE (Database & Cache)
        # Save Envelopes & Behavior for CURRENT turn (The actions taken)
        self._persist_envelopes(current_turn, turn_envelopes)
        
        # Increment Turn to Next State (Result of actions)
        self.world.turn += 1
        next_turn = self.world.turn
        
        # Save Snapshot of NEXT turn (The resulting world state)
        self._persist_snapshot(next_turn)
        
        # Cache Update: We associate Envelopes of T1 with T1.
        # And World State T2 with T2.
        # Basic caching (overwriting or appending)
        # Ideally, update cache for current_turn with envelopes? 
        # For simple logic: just cache the NEW state as next turn.
        self._cache_turn(next_turn, []) # Cache new state
        self.cache.update_turn_envelopes(current_turn, turn_envelopes, self._calculate_behaviors(turn_envelopes))
        
        print(f"--- TURN {current_turn} COMPLETE ---")
        


    def run(self, steps: int = 1):
        """Runs the simulation for N steps."""
        for _ in range(steps):
            self.step()
    
    # --- CACHE ACCESS METHODS ---
    
    def get_cached_world(self, turn: int):
        """Get WorldState from cache (fast, no DB query)."""
        return self.cache.get_world_at_turn(turn)
    
    def get_cached_envelopes(self, turn: int) -> List[CountryEnvelope]:
        """Get envelopes from cache (fast, no DB query)."""
        return self.cache.get_envelopes_at_turn(turn)
    
    def get_nation_envelope_history(
        self, 
        nation_id: str, 
        n_turns: Optional[int] = None
    ) -> List[CountryEnvelope]:
        """Get recent envelopes for a nation from cache."""
        return self.cache.get_envelopes_for_nation(nation_id, n_turns)
    
    def get_nation_behavior_history(self, nation_id: str) -> List[Dict]:
        """Get behavior metrics history for a nation from cache."""
        return self.cache.get_behaviors_for_nation(nation_id)
    
    def close(self):
        """Close database connection if open."""
        if self.db:
            self.db.close()
        
        # Save token usage at the end of simulation
        token_logger.save_to_csv()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
