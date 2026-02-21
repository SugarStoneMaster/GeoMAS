"""
Simulation Engine.

The Main Loop. Orchestrates the flow of time, agent decisions, and world updates.
"""

import random
from typing import Dict, List, Optional
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy
from geomas.agents.schemas.protocol import GovernmentType
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
from geomas.agents.context.events import ContextManager
from geomas.agents.opinion import OpinionAgent
from geomas.schemas.world import RelationshipState


class SimulationEngine:
    """
    The Main Loop. Orchestrates the flow of time, agent decisions, and world updates.
    
    Features:
    - Optional persistence via DuckDB when db_path is provided
    - In-events cache of recent turns for fast context access
    """

    def __init__(
        self, 
        map_seed: int = 42, 
        history_seed: int = 99, 
        n_cells: int = 1500,
        n_nations: int = 10,  # Added configurable n_nations
        llm_client: LLMClient = None,
        db_path: Optional[str] = None,
        simulation_id: Optional[int] = None,
        cache_size: int = 20,
        planned_scenario: Optional[dict] = None
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
            simulation_id: Optional existing ID. If None, a new one is created.
            cache_size: Number of recent turns to keep in events (default 20)
        """
        self.map_seed = map_seed
        self.history_seed = history_seed
        self.n_cells = n_cells
        self.n_nations = n_nations
        self.simulation_id = simulation_id
        self.planned_scenario = planned_scenario
        
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
        
        # 4. Initialize Context Manager (for LLM agent events)
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
        self.metrics_db = None
        if db_path:
            self._init_db(db_path)
            
            # Initialize Metrics DB in parallel
            try:
                from geomas.db.metrics_db import MetricsDB
                metrics_path = db_path.replace(".duckdb", "_metrics.duckdb")
                self.metrics_db = MetricsDB(metrics_path)
                print(f"[DB] Initialized Telemetry DB: {metrics_path}")
            except Exception as e:
                print(f"[DB ERROR] Failed to initialize MetricsDB: {e}")

    def _init_db(self, db_path: str) -> None:
        """Initialize database and save initial snapshot (turn 0)."""
        self.db = SimulationDB(db_path)
        self.db.initialize()
        
        # Get or Create Simulation ID
        import json
        is_new_sim = self.simulation_id is None
        if is_new_sim:
            self.simulation_id = self.db.create_simulation(
                genesis_seed=self.map_seed,
                simulation_seed=self.history_seed,
                n_cells=self.n_cells,
                n_nations=self.n_nations,
                scenario_json=json.dumps(self.planned_scenario) if self.planned_scenario else None
            )
            print(f"[DB] Saved as Simulation ID: {self.simulation_id}")
            
            # Save initial world state (turn 1 - Genesis) only for NEW simulations
            snapshot = serialize_world_snapshot(self.world, self.context_manager)
            self.db.save_snapshot(
                simulation_id=self.simulation_id,
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
        else:
            # For existing simulations, load planned scenario metadata
            info = self.db.get_simulation_info(self.simulation_id)
            if info and info.get("scenario_json"):
                import json
                self.planned_scenario = json.loads(info["scenario_json"])

    def _init_agents(self):
        """Creates a NationAgent for each nation in the world."""
        from geomas.calculators.analytics import calculate_power_projection, calculate_nation_aggregates
        
        # 1. Deterministic Ranking by Power Projection
        # Recalculate to ensure accuracy after genesis
        for nation in self.world.nations.values():
            aggr = calculate_nation_aggregates(nation, self.world)
            nation.total_population = aggr["total_population"]
            nation.total_soldiers = aggr["total_soldiers"]
            nation.total_aircraft = aggr["total_aircraft"]
            nation.total_navy = aggr["total_navy"]
            nation.power_projection = calculate_power_projection(nation)

        # Sort nations by power (highest power first)
        # We use nation_id as secondary sort key for absolute determinism
        ranked_nations = sorted(
            self.world.nations.keys(),
            key=lambda nid: (self.world.nations[nid].power_projection, nid),
            reverse=True
        )
        n_nations = len(ranked_nations)
        
        # Determinisitic Setup Profiles mapped to number of nations
        setup_profiles = {
            4: [
                (GlobalStrategy.TOTAL_EXPANSIONISM, GovernmentType.AUTHORITARIAN),
                (GlobalStrategy.COALITION_BUILDER, GovernmentType.DEMOCRACY),
                (GlobalStrategy.ARMED_ISOLATIONISM, GovernmentType.THEOCRACY),
                (GlobalStrategy.SCORCHED_EARTH, GovernmentType.AUTHORITARIAN),
            ],
            6: [
                (GlobalStrategy.TOTAL_EXPANSIONISM, GovernmentType.AUTHORITARIAN),
                (GlobalStrategy.TOTAL_EXPANSIONISM, GovernmentType.DEMOCRACY),
                (GlobalStrategy.COALITION_BUILDER, GovernmentType.DEMOCRACY),
                (GlobalStrategy.COALITION_BUILDER, GovernmentType.DEMOCRACY),
                (GlobalStrategy.ARMED_ISOLATIONISM, GovernmentType.THEOCRACY),
                (GlobalStrategy.SCORCHED_EARTH, GovernmentType.AUTHORITARIAN),
            ],
            8: [
                (GlobalStrategy.TOTAL_EXPANSIONISM, GovernmentType.AUTHORITARIAN),
                (GlobalStrategy.TOTAL_EXPANSIONISM, GovernmentType.DEMOCRACY),
                (GlobalStrategy.COALITION_BUILDER, GovernmentType.DEMOCRACY),
                (GlobalStrategy.COALITION_BUILDER, GovernmentType.DEMOCRACY),
                (GlobalStrategy.COALITION_BUILDER, GovernmentType.DEMOCRACY),
                (GlobalStrategy.ARMED_ISOLATIONISM, GovernmentType.DEMOCRACY),
                (GlobalStrategy.ARMED_ISOLATIONISM, GovernmentType.THEOCRACY),
                (GlobalStrategy.SCORCHED_EARTH, GovernmentType.AUTHORITARIAN),
            ]
        }
        
        nation_ids = sorted(list(self.world.nations.keys()))
        n_nations = len(nation_ids)
        
        # 2. Determine Profiles to Use (ordered by 'intensity')
        if n_nations in setup_profiles:
            combined_profiles = setup_profiles[n_nations] # Use original order (Expansionism first)
            assigned_strategies = [p[0] for p in combined_profiles]
            assigned_govs = [p[1] for p in combined_profiles]

        else:
            # --- FALLBACK LOGIC for non-standard n_nations (e.g. 5, 7, 10) ---
            # Order: High Power Profile -> Low Power Profile
            base_priority = [
                GlobalStrategy.TOTAL_EXPANSIONISM,
                GlobalStrategy.COALITION_BUILDER,
                GlobalStrategy.ARMED_ISOLATIONISM,
                GlobalStrategy.SCORCHED_EARTH
            ]
            fill_strategies = [GlobalStrategy.TOTAL_EXPANSIONISM, GlobalStrategy.COALITION_BUILDER]
            
            assigned_strategies = []
            for i in range(min(n_nations, 4)): 
                assigned_strategies.append(base_priority[i])
            for i in range(n_nations - len(assigned_strategies)): 
                assigned_strategies.append(fill_strategies[i % 2])
            
            # Simple government assignment (can be refined but keeps it logic)
            gov_pool = [GovernmentType.DEMOCRACY, GovernmentType.AUTHORITARIAN, GovernmentType.THEOCRACY]
            assigned_govs = []
            for i in range(n_nations):
                assigned_govs.append(gov_pool[i % 3])
        
        # 3. Create Agents for Ranked Nations
        for i, nation_id in enumerate(ranked_nations):
            strategy = assigned_strategies[i]
            gov_type = assigned_govs[i]
            
            # Store government_type on nation state for reference
            self.world.nations[nation_id].government_type = gov_type.value
            
            print(f"[INIT] {nation_id} Strategy: {strategy.value} | Gov: {gov_type.value}")
            
            self.agents[nation_id] = NationAgent(
                nation_id=nation_id,
                world=self.world,
                llm_client=self.client,
                global_strategy=strategy,
                context_manager=self.context_manager,
                government_type=gov_type
            )
    
    def _init_opinion_agents(self):
        """Creates an OpinionAgent for each nation."""
        for nation_id, nation in self.world.nations.items():
            # Get cultural traits from nation if available, else empty list
            traits = getattr(nation, 'cultural_traits', []) or []
            
            # Get government_type from nation state (set during _init_agents)
            gov_type_str = getattr(nation, 'government_type', None)
            gov_type = GovernmentType(gov_type_str) if gov_type_str else None
            
            self.opinion_agents[nation_id] = OpinionAgent(
                nation_id=nation_id,
                nation_name=nation.name,
                cultural_traits=traits,
                llm_client=self.client,
                world=self.world,
                government_type=gov_type
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
                envelope.foreign_private_intent
            )
            
            behaviors[envelope.sender_id] = {
                "deception_total": detailed["total"],
                "deception_defense": detailed["defense"],
                "deception_foreign": detailed["foreign"],
                "coherence_score": coherence,
                "global_strategy": envelope.global_strategy.value,
                "government_type": envelope.government_type
            }
        
        return behaviors

    def _persist_envelopes(self, turn: int, envelopes: List[CountryEnvelope]) -> None:
        """Save envelopes and behaviors for a turn."""
        if self.db is None: return
        
        for envelope in envelopes:
            self.db.save_envelope(
                simulation_id=self.simulation_id,
                turn=turn, 
                nation_id=envelope.sender_id, 
                envelope_json=serialize_envelope(envelope)
            )
            
            detailed = DeceptionAnalyzer.calculate_detailed_score(envelope)
            coherence = CoherenceAnalyzer.calculate_score(
                envelope.global_strategy,
                envelope.defense_private_intent,
                envelope.foreign_private_intent
            )
            self.db.save_behavior(
                simulation_id=self.simulation_id,
                turn=turn, nation_id=envelope.sender_id,
                deception_total=detailed["total"], deception_defense=detailed["defense"],
                deception_foreign=detailed["foreign"],
                coherence_score=coherence, global_strategy=envelope.global_strategy.value,
                government_type=envelope.government_type
            )
            
        # --- NEW TELEMETRY INSERTION ---
        if self.metrics_db:
            try:
                from geomas.calculators.metrics import extract_nation_metrics
                
                # 1. Nation Metrics
                nation_metrics_list = []
                # Keep running totals for global aggregates
                tot_deception = 0.0
                tot_coherence = 0.0
                tot_satisfaction = 0.0
                
                for envelope in envelopes:
                    m = extract_nation_metrics(self.world, envelope, turn)
                    if m:
                        nation_metrics_list.append(m)
                        tot_deception += m["deception_overall"]
                        tot_coherence += m["coherence_score"]
                        tot_satisfaction += m["public_satisfaction"]
                
                if nation_metrics_list:
                    self.metrics_db.insert_nation_metrics(self.simulation_id, nation_metrics_list)
                    
                # 2. Global Metrics
                n_count = len(envelopes)
                if n_count > 0:
                    global_data = {
                        "global_deception_avg": tot_deception / n_count,
                        "global_coherence_avg": tot_coherence / n_count,
                        "global_satisfaction_avg": tot_satisfaction / n_count,
                        # Detailed events like territories changed would require comparing T and T-1 WorldStates,
                        # skipping for now to prioritize Agent Metrics, or could be extracted from EventLogs.
                        "territories_changed_hands": 0, 
                        "units_created": sum(m["military_spending"] for m in nation_metrics_list), # Rough proxy
                        "units_destroyed": 0,
                        "global_trade_volume": sum(m["trade_volume"] for m in nation_metrics_list)
                    }
                    self.metrics_db.insert_global_metrics(self.simulation_id, turn, global_data)
                    
                # 3. Trust Metrics
                trust_data = []
                for observer_id, targets in self.world.trust_matrix.items():
                    for target_id, trust_val in targets.items():
                        rel = self.world.relationship_matrix.get(observer_id, {}).get(target_id, RelationshipState.PEACE)
                        trust_data.append({
                            "observer_id": observer_id,
                            "target_id": target_id,
                            "trust_value": trust_val,
                            "relationship_state": rel.value if hasattr(rel, 'value') else str(rel)
                        })
                self.metrics_db.insert_trust_metrics(self.simulation_id, turn, trust_data)
                
            except Exception as e:
                print(f"[METRICS ERROR] Failed to insert telemetry for turn {turn}: {e}")

    def _persist_token_usage(self, turn: int) -> None:
        """Save token usage records for a turn to DB."""
        if self.db is None: return
        from geomas.analysis.token_logger import token_logger
        
        # Determine cost based on model (simplified)
        for entry in token_logger.entries:
            if entry.turn == turn:
                # Mock cost calculation
                rate_in = 0.00015 / 1000 # $0.15 per million
                rate_out = 0.0006 / 1000 # $0.60 per million
                cost = (entry.input_tokens * rate_in) + (entry.output_tokens * rate_out)
                
                self.db.save_token_usage(
                    simulation_id=self.simulation_id,
                    turn=entry.turn,
                    nation_id=entry.nation_id,
                    agent_type=entry.role,
                    prompt_tokens=entry.input_tokens,
                    completion_tokens=entry.output_tokens,
                    total_tokens=entry.total_tokens,
                    model=entry.model,
                    cost=cost
                )

    def _persist_snapshot(self, turn: int) -> None:
        """Save world snapshot for a turn."""
        if self.db is None: return
        snapshot = serialize_world_snapshot(self.world, self.context_manager)
        self.db.save_snapshot(simulation_id=self.simulation_id, turn=turn, **snapshot)

    def _cache_turn(self, turn: int, envelopes: List[CountryEnvelope]) -> None:
        """Add turn data to in-events cache."""
        behaviors = self._calculate_behaviors(envelopes)
        self.cache.add_turn(
            turn=turn,
            world_state=self.world,
            envelopes=envelopes,
            behaviors=behaviors
        )

    def _apply_ambiguity_penalty(self):
        """
        Applies a trust penalty to nations that have a MUTUAL_DEFENSE pact 
        but remain neutral while their ally is at war.
        """
        from geomas.schemas.world import RelationshipState
        
        for nation_id, relationships in self.world.relationship_matrix.items():
            # X is at war with someone (Z)
            enemies = [target_id for target_id, rel in relationships.items() if rel == RelationshipState.WAR]
            if not enemies:
                continue
                
            # Check allies of X
            for ally_id, rel_with_ally in relationships.items():
                if rel_with_ally == RelationshipState.MUTUAL_DEFENSE:
                    # Ally Y is NOT at war with ANY of X's enemies
                    ally_relationships = self.world.relationship_matrix.get(ally_id, {})
                    is_helping = any(ally_relationships.get(enemy_id) == RelationshipState.WAR for enemy_id in enemies)
                    
                    if not is_helping:
                        # Ambiguity Detected
                        ally_nation = self.world.nations.get(ally_id)
                        if ally_nation:
                            current_streak = ally_nation.betrayal_tracker.get(nation_id, 0) + 1
                            ally_nation.betrayal_tracker[nation_id] = current_streak
                            
                            if current_streak >= 3:
                                # TRIGGER GLOBAL BETRAYAL
                                self._execute_global_betrayal(ally_id, nation_id)
                                # Reset tracker after execution to avoid double pounding immediately
                                ally_nation.betrayal_tracker[nation_id] = 0
                            else:
                                # Normal Penalty
                                penalty = -2.0
                                self.engine.adjust_trust(nation_id, ally_id, penalty)
                                self.turn_logs.append(
                                    f"📉 [DIPLOMACY] {nation_id} trust in {ally_id} decreased by {penalty:+.1f} "
                                    f"(Ambiguity Penalty: ally not joined in war. Warning {current_streak}/3)."
                                )
                    else:
                        # Ally IS helping -> Reset tracker
                        ally_nation = self.world.nations.get(ally_id)
                        if ally_nation and nation_id in ally_nation.betrayal_tracker:
                             ally_nation.betrayal_tracker[nation_id] = 0

    def _execute_global_betrayal(self, traitor_id: str, victim_id: str):
        """
        Executes the consequences of a Global Betrayal (ignoring Mutual Defense for 3 turns).
        1. Break Alliance (Trust -> 0, Rel -> PEACE).
        2. Global Trust Penalty (-30) from ALL nations.
        3. Global Event Log.
        """
        # 1. Break Alliance
        self.world.relationship_matrix[traitor_id][victim_id] = RelationshipState.PEACE
        self.world.relationship_matrix[victim_id][traitor_id] = RelationshipState.PEACE
        self.engine.adjust_trust(victim_id, traitor_id, -50.0) # Massive hit
        
        # 2. Global Penalty
        for observer_id in self.agents.keys():
            if observer_id == traitor_id: continue
            if observer_id == victim_id: continue
            
            # Everyone loses trust in the traitor
            self.engine.adjust_trust(observer_id, traitor_id, -30.0)
            
        # 3. Log
        msg = f"🌍 [BETRAYAL] {traitor_id} has abandoned {victim_id} to their fate! The world condemns this treachery. (Mutual Defense Pact Broken)."
        self.turn_logs.append(msg)
        self.world.global_events.append(f"T{self.world.turn}: {msg}")

    def step(self, injections: Optional[List[dict]] = None, scenario_trigger: Optional[dict] = None):
        """Executes one full turn of the simulation."""
        
        current_turn = self.world.turn
        
        print(f"--- STARTING TURN {current_turn} ---")
        self.turn_logs.append(f"--- TURN {current_turn} ---")
        
        # Local RNG for turn determinism (shuffle order) using all simulation parameters
        combined_seed = f"{self.map_seed}-{self.history_seed}-{self.n_cells}-{current_turn}"
        turn_rng = random.Random(combined_seed)
        
        # -1. SCENARIO PHASE (Mid-Simulation Triggers like Pandemics)
        # Priority: explicit argument > persisted state
        trigger = scenario_trigger or self.planned_scenario
        
        if trigger is not None:
            from geomas.simulation.scenarios import check_and_trigger_scenario
            scenario_result = check_and_trigger_scenario(self.world, self.context_manager, current_turn, trigger)
            
            # 1. Handle Logs
            scenario_logs = scenario_result.get("logs", [])
            if scenario_logs:
                for msg in scenario_logs:
                    print(msg)
                self.turn_logs.extend(scenario_logs)
                
            # 2. Handle Dynamic Nation Creation (Insurrection)
            new_nation_data = scenario_result.get("new_nation")
            if new_nation_data:
                rebel_id = new_nation_data["id"]
                rebel_strategy = new_nation_data["strategy"]
                rebel_gov = new_nation_data["government_type"]
                
                print(f"[SCENARIO] Initializing new Rebel Agent: {rebel_id}")
                
                # Instantiate NationAgent
                self.agents[rebel_id] = NationAgent(
                    nation_id=rebel_id,
                    world=self.world,
                    llm_client=self.client,
                    global_strategy=rebel_strategy,
                    context_manager=self.context_manager,
                    government_type=rebel_gov
                )
                
                # Instantiate OpinionAgent
                nation_state = self.world.nations[rebel_id]
                self.opinion_agents[rebel_id] = OpinionAgent(
                    nation_id=rebel_id,
                    nation_name=nation_state.name,
                    cultural_traits=nation_state.cultural_traits,
                    llm_client=self.client,
                    world=self.world,
                    government_type=rebel_gov
                )
                
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
                envelope = agent.act(current_turn, injections)
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
        
        # 3. DIPLOMATIC DECAY (Ambiguity Penalty)
        self._apply_ambiguity_penalty()
        
        # 4. CONTEXT PHASE (Update agent events)
        self.context_manager.update_after_turn(current_turn, turn_envelopes, self.world)
        
        # 5. OPINION PHASE (Population reaction - post execution)
        # We capture prompts from opinion_agents after they react
        run_opinion_phase(
            self.world,
            self.turn_logs,
            self.opinion_agents,
            turn_envelopes,
            turn=current_turn
        )
        
        # Inject Opinion prompts into envelopes before persistence
        for env in turn_envelopes:
            o_agent = self.opinion_agents.get(env.sender_id)
            if o_agent:
                # Basic Prompts
                env.opinion_system_prompt = getattr(o_agent, 'last_system_prompt', None)
                env.opinion_input_prompt = getattr(o_agent, 'last_input_prompt', None)
                
                # Detailed Metrics from Nation State or Agent Perception
                # (The Opinion Agent reaction results are already applied to NationState)
                nation = self.world.nations.get(env.sender_id)
                if nation:
                    env.opinion_multiplier_increase = nation.population_multiplier_increase
                    env.opinion_multiplier_decrease = nation.population_multiplier_decrease
                
                # We need to capture the mood/reasoning/raw_json from the last execution
                # I'll update OpinionAgent to store the full LAST RESPONSE for easiest access.
                last_resp = getattr(o_agent, 'last_response', None)
                if last_resp:
                    env.opinion_mood = last_resp.mood
                    env.opinion_reasoning = last_resp.reasoning
                    env.raw_opinion_response = last_resp.raw_json
        
        # 6. PERSIST PHASE (Database)
        # 6. PERSIST PHASE (Database & Cache)
        # Save Envelopes & Behavior for CURRENT turn (The actions taken)
        self._persist_envelopes(current_turn, turn_envelopes)
        self._persist_token_usage(current_turn)
        
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
        
    def load_state(self, turn: int, from_simulation_id: Optional[int] = None):
        """
        Recreates simulation state (world, events, cache) from a specific turn in DB.
        Enables continuation or forking from history.
        
        Args:
            turn: The turn number to load state from.
            from_simulation_id: If provided, load from a different simulation ID (Forking).
                                Defaults to current self.simulation_id.
        """
        if not self.db:
            raise ValueError("No database connected to load state from")
        
        sim_id_to_load = from_simulation_id if from_simulation_id is not None else self.simulation_id
            
        # 1. Load Snapshot
        data = self.db.load_snapshot(sim_id_to_load, turn)
        if not data:
            raise ValueError(f"Snapshot for turn {turn} not found in DB")
            
        # 2. Reconstruct World
        from geomas.db.serialization import deserialize_world_snapshot, deserialize_memory_state
        import json
        
        world_events = json.loads(data["world_events_json"])
        self.world = deserialize_world_snapshot(
            provinces_json=data["provinces_json"],
            nations_json=data["nations_json"],
            trust_matrix_json=data["trust_matrix"],
            relationship_matrix_json=data["relationship_matrix"],
            turn=turn,
            global_events=world_events
        )
        
        # 3. Reconstruct Memory
        memory_state = deserialize_memory_state(data["memory_json"])
        self.context_manager.load_state(memory_state)
        
        # 4. Re-initialize Engine and Agents
        self.engine = ActionEngine(self.world)
        self._init_agents()
        self._init_opinion_agents()
        
        from geomas.db.serialization import deserialize_envelope
        self.history = []
        for t in range(1, turn):
            envelopes_data = self.db.load_envelopes(sim_id_to_load, t)
            turn_enps = []
            for _, enp_json in envelopes_data:
                envelope = deserialize_envelope(enp_json)
                turn_enps.append(envelope)
                
                # 4c. Restore Trace History to Agents for XAI Dashboard
                agent = self.agents.get(envelope.sender_id)
                if agent:
                    # Construct Trace for NationAgent
                    trace = {
                        "turn": t,
                        "nation_id": envelope.sender_id,
                        "president": {
                            "system_prompt": envelope.last_system_prompt,
                            "user_prompt": envelope.last_input_prompt,
                            "raw_json": envelope.raw_president_response,
                            "decree": envelope.raw_president_response,
                            "public_statement": envelope.public_statement
                        },
                        "defense": {
                            "system_prompt": envelope.defense_system_prompt,
                            "user_prompt": envelope.defense_input_prompt,
                            "raw_json": envelope.raw_defense_response,
                            "proposal": envelope.original_defense_proposal
                        },
                        "economy": {
                            "system_prompt": envelope.economic_system_prompt,
                            "user_prompt": envelope.economic_input_prompt,
                            "raw_json": envelope.raw_economic_response,
                            "proposal": envelope.original_economic_proposal
                        },
                        "foreign": {
                            "system_prompt": envelope.foreign_system_prompt,
                            "user_prompt": envelope.foreign_input_prompt,
                            "raw_json": envelope.raw_foreign_response,
                            "proposal": envelope.original_foreign_proposal
                        },
                        "envelope": envelope
                    }
                    agent.trace_history[t] = trace
                    
                # Construct Trace for OpinionAgent
                o_agent = self.opinion_agents.get(envelope.sender_id)
                if o_agent:
                    o_agent.trace_history[t] = {
                        "system_prompt": envelope.opinion_system_prompt,
                        "user_prompt": envelope.opinion_input_prompt,
                        "proposal": {
                            "mood": envelope.opinion_mood,
                            "reasoning": envelope.opinion_reasoning,
                            "multiplier_increase": envelope.opinion_multiplier_increase,
                            "multiplier_decrease": envelope.opinion_multiplier_decrease,
                            "raw_json": envelope.raw_opinion_response
                        }
                    }
            self.history.append(turn_enps)
        
        # 5. Sync Cache
        self.cache.clear()
        self.cache.add_turn(turn, self.world, [], {}) 
        
        print(f"🔄 [SYSTEM] Simulation state restored to turn {turn}")
        

    def run(self, steps: int = 1, injections: Optional[List[dict]] = None):
        """Runs the simulation for N steps."""
        for _ in range(steps):
            self.step(injections)
    
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
    def close(self):
        """Close database connection if open."""
        if self.db:
            self.db.close()
        if hasattr(self, 'metrics_db') and self.metrics_db:
            self.metrics_db.close()
        
        # Save token usage at the end of simulation
        token_logger.save_to_csv()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
