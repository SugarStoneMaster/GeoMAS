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
        planned_scenario: Optional[dict] = None,
        read_only: bool = False
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
            planned_scenario: Optional scenario configuration
            read_only: If True, connects to DB in read-only mode (doesn't lock)
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
        
        # Link Context Manager to Engine
        self.engine.context_manager = self.context_manager
        
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
        self.read_only = read_only
        if db_path:
            self._init_db(db_path, read_only=read_only)
            
            # Initialize Metrics DB in parallel
            try:
                from geomas.db.metrics_db import MetricsDB
                metrics_path = db_path.replace(".duckdb", "_metrics.duckdb")
                self.metrics_db = MetricsDB(metrics_path, read_only=read_only)
                print(f"[DB] Initialized Telemetry DB: {metrics_path} (read_only={read_only})")
            except Exception as e:
                print(f"[DB ERROR] Failed to initialize MetricsDB: {e}")

    def _init_db(self, db_path: str, read_only: bool = False) -> None:
        """Initialize database and save initial snapshot (turn 0)."""
        self.db = SimulationDB(db_path, read_only=read_only)
        
        # Only initialize schema and create sim if NOT in read_only mode
        if not read_only:
            self.db.initialize()
        
        # Get or Create Simulation ID
        import json
        is_new_sim = self.simulation_id is None
        if is_new_sim and not read_only:
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
        from geomas.agents.schemas import GlobalStrategy
        from geomas.agents.schemas.protocol import GovernmentType

        # 1. Determine if we need to perform initial assignment (ranking/nukes)
        # We assign if any nation is missing a valid strategy (Turn 0 or mocked tests)
        needs_assignment = any(
            not isinstance(n.global_strategy, (str, GlobalStrategy))
            for n in self.world.nations.values()
        )
        
        if needs_assignment:
            # Deterministic Ranking by Power Projection
            for nation in self.world.nations.values():
                aggr = calculate_nation_aggregates(nation, self.world)
                # Handle potential mock values for aggregates
                nation.total_population = aggr.get("total_population", 0)
                nation.total_soldiers = aggr.get("total_soldiers", 0)
                nation.total_aircraft = aggr.get("total_aircraft", 0)
                nation.total_navy = aggr.get("total_navy", 0)
                nation.power_projection = calculate_power_projection(nation)

            # Sort nations by power (highest power first)
            def get_power(nid):
                p = getattr(self.world.nations[nid], 'power_projection', 0.0)
                return p if isinstance(p, (int, float)) else 0.0

            ranked_nations = sorted(
                self.world.nations.keys(),
                key=lambda nid: (get_power(nid), nid),
                reverse=True
            )
            
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
                    (GlobalStrategy.TOTAL_EXPANSIONISM, GovernmentType.THEOCRACY),
                    (GlobalStrategy.SCORCHED_EARTH, GovernmentType.AUTHORITARIAN),
                ]
            }
            
            nation_ids = sorted(list(self.world.nations.keys()))
            n_nations = len(nation_ids)
            
            if n_nations in setup_profiles:
                combined_profiles = setup_profiles[n_nations]
                assigned_strategies = [p[0] for p in combined_profiles]
                assigned_govs = [p[1] for p in combined_profiles]
            else:
                # FALLBACK LOGIC for non-standard n_nations
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
                
                gov_pool = [GovernmentType.DEMOCRACY, GovernmentType.AUTHORITARIAN, GovernmentType.THEOCRACY]
                assigned_govs = []
                for i in range(n_nations):
                    assigned_govs.append(gov_pool[i % 3])
            
            # Persist assigned values back to NationState
            for i, nation_id in enumerate(ranked_nations):
                self.world.nations[nation_id].global_strategy = assigned_strategies[i].value
                self.world.nations[nation_id].government_type = assigned_govs[i].value

        # 2. Re-create Agents (Always, for both new and restored sims)
        for nation_id, nation in self.world.nations.items():
            # Robust casting for strings/enums/mocks
            strat_val = nation.global_strategy
            if hasattr(strat_val, "value"): strat_val = strat_val.value
            strategy = GlobalStrategy(strat_val)
            
            gov_val = nation.government_type
            if hasattr(gov_val, "value"): gov_val = gov_val.value
            gov_type = GovernmentType(gov_val)
            
            print(f"[INIT] {nation_id} Strategy: {strategy.value} | Gov: {gov_type.value}")
            
            self.agents[nation_id] = NationAgent(
                nation_id=nation_id,
                world=self.world,
                llm_client=self.client,
                global_strategy=strategy,
                context_manager=self.context_manager,
                government_type=gov_type
            )
            
        # 3. Nuclear Calibration (only on Turn 0/1, i.e. new simulation)
        # world_turn <= 1 ensures we don't re-assign on mid-game restore.
        # has_nukes guard is removed: world generation no longer pre-assigns nukes,
        # so the strategic assignment is always needed at boot.
        world_turn = getattr(self.world, 'turn', 0)
        if not isinstance(world_turn, int): world_turn = 0

        # Also skip if strategic nukes already assigned (mid-game world where someone has nukes)
        def get_nukes(n):
            val = getattr(n, 'nukes', 0)
            return val if isinstance(val, int) else 0
        has_nukes = any(get_nukes(n) > 0 for n in self.world.nations.values())

        if world_turn <= 1 and not has_nukes:
            # STRATEGIC ASSIGNMENT (Hardcoded as per user instructions)
            # Goal: 3 Stable Primary Nuclear Powers: SE/Auth, TE/Auth, AI/Demo
            nuke_recipients = []
            
            def get_strat_gov(agent):
                s = str(agent.strategy.value if hasattr(agent.strategy, "value") else agent.strategy)
                g = str(agent.government_type.value if hasattr(agent.government_type, "value") else agent.government_type)
                return s, g

            all_nids = sorted(self.agents.keys())
            
            # 1. Identify specific targets
            se_auth = None
            te_auth = None
            ai_demo = None
            
            for nid in all_nids:
                s, g = get_strat_gov(self.agents[nid])
                if s == "SCORCHED_EARTH" and g == "AUTHORITARIAN":
                    se_auth = nid
                elif s == "TOTAL_EXPANSIONISM" and g == "AUTHORITARIAN":
                    te_auth = nid
                elif s == "ARMED_ISOLATIONISM" and g == "DEMOCRACY":
                    ai_demo = nid

            # Collect in order
            if se_auth: nuke_recipients.append(se_auth)
            if te_auth: nuke_recipients.append(te_auth)
            if ai_demo: nuke_recipients.append(ai_demo)

            print(f"[DEBUG] Nuke Calibration Targets -> SE/Auth: {se_auth}, TE/Auth: {te_auth}, AI/Demo: {ai_demo}")
            
            # Deterministic Count Generation
            import random
            nuke_rng = random.Random(self.map_seed + self.history_seed + 999) 
            
            # Assignment
            n_nations = len(self.world.nations)
            for nid in nuke_recipients:
                if n_nations >= 8:
                    self.world.nations[nid].nukes = nuke_rng.randint(50, 100)
                else:
                    self.world.nations[nid].nukes = nuke_rng.randint(2, 5)
                    
                strat, gov = get_strat_gov(self.agents[nid])
                print(f"[INIT] {nid} ({strat}/{gov}) assigned {self.world.nations[nid].nukes} Nuclear Weapons (Strict Requirement).")
            
    
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
                n_count = len(nation_metrics_list)
                if n_count > 0:
                    # Parse current turn events for global KPIs
                    territories_changed = 0
                    units_destroyed = 0
                    
                    for envelope in envelopes:
                        # Extract units destroyed and territory changes directly from deterministic execution outcomes
                        if getattr(envelope, "defense_payload", None) and getattr(envelope.defense_payload, "moves", None):
                            for move in envelope.defense_payload.moves:
                                outcome = getattr(move, "execution_outcome", None)
                                if outcome and outcome.status == "SUCCESS" and outcome.details:
                                    # Increment killed units (from all branches: land, sea, air)
                                    units_destroyed += outcome.details.get("attacker_losses", 0)
                                    units_destroyed += outcome.details.get("defender_losses", 0)
                                    units_destroyed += outcome.details.get("attacker_losses_navy", 0)
                                    
                                    # Increment territory changes if conquest occurred
                                    if outcome.details.get("attacker_wins") is True:
                                        action_type = getattr(move, "action_type", None)
                                        action_str = action_type.value if hasattr(action_type, "value") else str(action_type)
                                        unit_type = getattr(move, "unit_type", None)
                                        unit_str = unit_type.value if hasattr(unit_type, "value") else str(unit_type)
                                        
                                        # Air strikes don't conquer land, only soldiers and naval landings do
                                        if action_str == "MOVE_TROOPS" and unit_str != "AIRCRAFT":
                                            territories_changed += 1

                    global_data = {
                        "global_deception_avg": tot_deception / n_count,
                        "global_coherence_avg": tot_coherence / n_count,
                        "global_satisfaction_avg": tot_satisfaction / n_count,
                        "territories_changed_hands": territories_changed, 
                        "units_created": sum(m["military_spending"] for m in nation_metrics_list), # Rough proxy
                        "units_destroyed": units_destroyed,
                        "global_trade_volume": sum(m["trade_volume"] for m in nation_metrics_list)
                    }
                    self.metrics_db.insert_global_metrics(self.simulation_id, turn, global_data)
                    
                # 3. Trust Metrics
                trust_data = []
                for observer_id, targets in self.world.trust_matrix.items():
                    obs_nation = self.world.nations.get(observer_id)
                    if not obs_nation or not obs_nation.is_active:
                        continue
                    for target_id, trust_val in targets.items():
                        target_nation = self.world.nations.get(target_id)
                        if not target_nation or not target_nation.is_active:
                            continue
                        rel = self.world.relationship_matrix.get(observer_id, {}).get(target_id, RelationshipState.PEACE)
                        trust_data.append({
                            "observer_id": observer_id,
                            "target_id": target_id,
                            "trust_value": trust_val,
                            "relationship_state": rel.value if hasattr(rel, 'value') else str(rel)
                        })
                self.metrics_db.insert_trust_metrics(self.simulation_id, turn, trust_data)

                # 4. Action Outcomes (engine-level accept/reject per individual action)
                from geomas.calculators.metrics import (
                    extract_action_outcomes,
                    extract_presidential_decisions,
                )
                action_outcome_rows = []
                presidential_decision_rows = []
                for envelope in envelopes:
                    action_outcome_rows.extend(extract_action_outcomes(envelope, turn))
                    presidential_decision_rows.extend(
                        extract_presidential_decisions(envelope, turn)
                    )
                self.metrics_db.insert_action_outcomes(
                    self.simulation_id, action_outcome_rows
                )

                # 5. Presidential Decisions (APPROVE/VETO per domain)
                self.metrics_db.insert_presidential_decisions(
                    self.simulation_id, presidential_decision_rows
                )
                
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

    def _apply_satisfaction_decay(self):
        """
        Applies a natural decay to public satisfaction every turn.
        Governments must actively invest in welfare to maintain high approval.
        """
        for nation in self.world.nations.values():
            if nation.is_active:
                # Natural entropy of public approval (-1.5 per month)
                nation.public_satisfaction = max(0.0, nation.public_satisfaction - 1.5)

    def _apply_ambiguity_penalty(self):
        """
        Applies a trust penalty to nations that have a MUTUAL_DEFENSE pact 
        but remain neutral while their ally is at war.
        """
        from geomas.schemas.world import RelationshipState
        
        for nation_id, relationships in self.world.relationship_matrix.items():
            # Skip inactive nations
            nation_x = self.world.nations.get(nation_id)
            if not nation_x or not nation_x.is_active:
                continue

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
                        # CROSS-ALLIANCE PROTECTION: 
                        # Only penalize if X is being ATTACKED (Victim).
                        # If X started the war, allies are NOT obliged to help.
                        mandatory_defence = False
                        nation_x = self.world.nations.get(nation_id)
                        if nation_x: # Ensure nation_x exists
                            for enemy_id in enemies:
                                war_stats = nation_x.active_wars.get(enemy_id)
                                if war_stats and war_stats.initiator_id != nation_id:
                                    # X is NOT the initiator -> X is the Victim. 
                                    mandatory_defence = True
                                    break
                        
                        if not mandatory_defence:
                            continue # No penalty for not helping an aggressor
                            
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
        1. Downgrade Alliance to NON_AGGRESSION.
        2. Local Trust Penalty (-30).
        3. Global Trust Penalty (-30) from ALL other nations.
        4. Global Event Log.
        """
        # 1. Downgrade Alliance
        self.world.relationship_matrix[traitor_id][victim_id] = RelationshipState.NON_AGGRESSION
        self.world.relationship_matrix[victim_id][traitor_id] = RelationshipState.NON_AGGRESSION
        self.engine.adjust_trust(victim_id, traitor_id, -30.0) # Severe hit, but recoverable
        
        # 2. Global Penalty
        for observer_id in self.agents.keys():
            if observer_id == traitor_id: continue
            if observer_id == victim_id: continue
            
            # Everyone loses trust in the traitor
            self.engine.adjust_trust(observer_id, traitor_id, -30.0)
            
        # 3. Log
        msg = f"🌍 [BETRAYAL] {traitor_id} has abandoned {victim_id} to their fate! The world condemns this treachery. (Mutual Defense Pact downgraded to Non-Aggression)."
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

            # 3. Handle Regime Change
            modified_nation_data = scenario_result.get("modified_nation")
            if modified_nation_data:
                target_id = modified_nation_data["id"]
                new_strat = modified_nation_data["strategy"]
                new_gov = modified_nation_data["government_type"]
                
                print(f"[SCENARIO] Regime Change for: {target_id}")
                agent = self.agents.get(target_id)
                if agent:
                    agent.change_regime(new_gov, new_strat)
                    
                op_agent = self.opinion_agents.get(target_id)
                if op_agent:
                    op_agent.government_type = new_gov
                
        # 0. UPKEEP PHASE (resources, consumption, crisis)
        run_upkeep_phase(self.world, self.turn_logs)
        
        # 0b. DIPLOMACY PHASE (Clear expired proposals)
        # Verify proposals from T-2 are removed before T start
        clear_expired_proposals(self.world)
        
        
        # 1. & 2. COMBINED SEQUENTIAL PHASE (Decision + Execution per Nation)
        # Shuffle nation IDs to ensure fairness in turn order
        nation_ids = [nid for nid in self.agents.keys() if self.world.nations[nid].is_active]
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
        self._apply_satisfaction_decay()
        
        # 4. CONTEXT PHASE (Update agent events)
        self.context_manager.update_after_turn(current_turn, turn_envelopes, self.world)
        
        # 4b. State-based Event Extraction (Unrest, Strikes, Crisis)
        # This ensures agents "perceive" these global events as context
        from geomas.agents.context.events.schemas import EventType, NotableEvent
        for n_id, nation in self.world.nations.items():
            if nation.civil_unrest_active:
                self.context_manager.global_events.append(NotableEvent(
                    turn=current_turn,
                    event_type=EventType.CIVIL_UNREST,
                    actors=[n_id],
                    summary=f"CIVIL UNREST in {nation.name}! Production halted."
                ))
            elif nation.public_satisfaction < 20: # THRESHOLD_GENERAL_STRIKE
                self.context_manager.global_events.append(NotableEvent(
                    turn=current_turn,
                    event_type=EventType.GENERAL_STRIKE,
                    actors=[n_id],
                    summary=f"GENERAL STRIKE in {nation.name}! Efficiency is low."
                ))
        
        # 5. OPINION PHASE (Population reaction - post execution)
        # We capture prompts from opinion_agents after they react
        run_opinion_phase(
            self.world,
            self.turn_logs,
            self.opinion_agents,
            turn_envelopes,
            turn=current_turn,
            seed=self.map_seed
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
            
        # 1. Load Simulation Metadata and Snapshot
        info = self.db.get_simulation_info(sim_id_to_load)
        if info:
            self.map_seed = info.get("genesis_seed", self.map_seed)
            self.history_seed = info.get("simulation_seed", self.history_seed)
            print(f"[LOAD] Restored Seeds -> Map: {self.map_seed}, History: {self.history_seed}")

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
        

    def run(self, steps: int = 1, injections: Optional[List[dict]] = None, scenario_trigger: Optional[dict] = None):
        """Runs the simulation for N steps, applying injections that have a valid duration."""
        active_injections = []
        if injections:
            import copy
            active_injections = copy.deepcopy(injections)
            # Default duration is 1 if not specified
            for inj in active_injections:
                if 'duration' not in inj:
                    inj['duration'] = 1

        for _ in range(steps):
            current_injections = [inj for inj in active_injections if inj['duration'] > 0]
            
            self.step(
                injections=copy.deepcopy(current_injections) if current_injections else None, 
                scenario_trigger=scenario_trigger
            )
            
            # Decrement duration after the step completes
            for inj in active_injections:
                inj['duration'] -= 1
    
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
    
    def fork(self, new_name: Optional[str] = None):
        """
        Creates a new simulation entry in the DB and copies history up to the current turn.
        Detaches the engine from the original simulation and starts a new one.
        """
        if not self.db:
            raise ValueError("Cannot fork without a database connection.")
            
        source_id = self.simulation_id
        current_turn = self.world.turn
        
        # 1. Create a NEW simulation entry
        import json
        info = self.db.get_simulation_info(source_id)
        
        # Determine forked name
        if not new_name:
            source_name = info.get("name", f"Sim {source_id}")
            new_name = f"{source_name} (Fork @T{current_turn})"
            
        new_id = self.db.create_simulation(
            genesis_seed=self.map_seed,
            simulation_seed=self.history_seed,
            n_cells=self.n_cells,
            n_nations=self.n_nations,
            name=new_name,
            scenario_json=json.dumps(self.planned_scenario) if self.planned_scenario else None
        )
        
        print(f"[ENGINE] Forking Sim {source_id} -> New Sim {new_id} at Turn {current_turn}")
        
        # 2. Copy history in DB
        self.db.copy_history_for_fork(source_id, new_id, current_turn)
        
        # 3. Handle Metrics DB (Forking telemetry)
        if self.metrics_db:
             try:
                 # Minimal forking for metrics: we just start fresh on the new simulation_id
                 # Copying gigabytes of metrics is expensive, typically we just want to see the new trend
                 print(f"[METRICS] Detaching telemetry for new Simulation {new_id}")
             except Exception as e:
                 print(f"[METRICS ERROR] Failed to fork metrics: {e}")
                 
        # 4. Switch the engine to the new simulation_id
        self.simulation_id = new_id
        
        # Clear engine-level logs to avoid mixing histories in memory
        self.turn_logs = [f"--- FORKED FROM SIM {source_id} AT TURN {current_turn} ---"]
        
        return new_id

    def fork_and_continue(
        self,
        source_simulation_id: int,
        fork_at_turn: int,
        n_turns: Optional[int] = None,
        injections: Optional[List[dict]] = None,
        scenario_trigger: Optional[dict] = None,
        new_name: Optional[str] = None,
        read_only: bool = False
    ) -> int:
        """
        High-level fork-and-continue workflow.

        Semantics:
          fork_at_turn=T means: load the world snapshot saved AT turn T.
          Since snapshot(T) represents the state AFTER agents acted on turn T-1,
          the next turn to execute will be T (the fork continues from turn T).

        Steps:
          1. Load world state from source_simulation_id at fork_at_turn.
          2. Fork into a new simulation entry in the DB.
          3. Compute remaining turns as max_turn(source) - fork_at_turn (unless n_turns is explicit).
          4. Run the simulation for the computed number of steps.

        Args:
            source_simulation_id: ID of the simulation to fork from.
            fork_at_turn: Snapshot turn to load (agents have acted through turn fork_at_turn - 1).
            n_turns: Steps to run after the fork. If None, runs until source's original max turn.
            injections: Optional XAI constraint injections forwarded to every step.
            scenario_trigger: Optional scenario dict forwarded to every step (checked inside step()).
            new_name: Optional friendly name for the forked simulation.

        Returns:
            The new simulation_id of the forked run.
        """
        if not self.db:
            raise ValueError("Cannot fork_and_continue without a database connection.")

        # Step 1 — Load state from the source simulation
        self.load_state(fork_at_turn, from_simulation_id=source_simulation_id)

        # Step 2 — Fork into a new simulation entry
        auto_name = new_name or f"Fork of Sim {source_simulation_id} @T{fork_at_turn}"
        new_id = self.fork(new_name=auto_name)

        # Step 3 — Determine how many turns to run
        if n_turns is None:
            source_max_turn = self.db.get_max_turn(source_simulation_id)
            n_turns = max(0, source_max_turn - fork_at_turn)

        print(
            f"[ENGINE] fork_and_continue: Sim {source_simulation_id} → #{new_id}"
            f" | Fork snapshot: T{fork_at_turn} | Next turn to execute: T{self.world.turn}"
            f" | Steps to run: {n_turns}"
        )

        if n_turns == 0:
            print("[ENGINE] fork_and_continue: n_turns=0, no steps will be executed.")
            return new_id

        # Step 4 — Run
        self.run(
            steps=n_turns,
            injections=injections,
            scenario_trigger=scenario_trigger,
        )

        return new_id

    def close(self) -> None:
        """Close database connections."""
        if self.db:
            self.db.close()
        if self.metrics_db:
            try:
                self.metrics_db.close()
            except:
                pass
        
        # Save token usage at the end of simulation
        token_logger.save_to_csv()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
