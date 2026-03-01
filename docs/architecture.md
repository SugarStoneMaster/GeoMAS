# 🏗 GeoMAS — Exhaustive Technical Architecture

GeoMAS is a multi-layered simulation environment built for structural determinism and cognitive depth. This document provides a **granular breakdown** of every system layer, its mathematical foundations, and inter-layer data flows.

---

## 1. Layer Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                   1. PRESENTATION LAYER                       │
│  Streamlit UI (web/)  │  Jupyter Notebooks (data/)           │
├──────────────────────────────────────────────────────────────┤
│                   2. ORCHESTRATION LAYER                      │
│  SimulationEngine (simulation/engine.py, 979 lines)          │
│  7-Phase Turn Loop  │  State Forking  │  Persistence         │
├──────────────────────────────────────────────────────────────┤
│                   3. COGNITIVE LAYER                          │
│  NationAgent → 3 Ministers + President (agents/)              │
│  OpinionAgent (population reaction)                          │
│  ContextManager (bounded rationality, 1058 lines)            │
│  LLMClient (multi-provider, 578 lines)                       │
├──────────────────────────────────────────────────────────────┤
│              4. SIMULATION PHYSICS LAYER                      │
│  ── Action System ──────────────────────────────────────     │
│  ActionEngine │ Defense (waterfall, 985 lines)               │
│  Economy Handler (295) │ Foreign Handler (619)               │
│  Opinion Handler (273) │ Validators (120)                    │
│  Calculators (pure, stateless, 450 lines total)              │
│  ── World Generation & Spatial ────────────────────────      │
│  MapGenerator (8-stage Voronoi pipeline)                     │
│  GenesisEngine (50-year history, 311 lines)                  │
│  SpatialManager (NetworkX graph, 176 lines)                  │
├──────────────────────────────────────────────────────────────┤
│              5. OBSERVABILITY LAYER                           │
│  ── Persistence ───────────────────────────────────────      │
│  WorldState/NationState/ProvinceState (Pydantic schemas)     │
│  SimulationDB (DuckDB, 430 lines)  │  MetricsDB (7.8KB)     │
│  TurnCache (in-memory) │ Serialization (8.9KB)               │
│  ── Behavioral Intelligence ───────────────────────────      │
│  DeceptionAnalyzer (197) │ CoherenceAnalyzer (75)           │
│  DeltaAnalyzer (185) │ BehaviorTracker (134)                │
│  SimulationHealthAnalyzer (98) │ TokenLogger (87)            │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Orchestration Layer — SimulationEngine

**File**: `geomas/simulation/engine.py` (1006+ lines)

### 2.1 Initialization Sequence
```python
SimulationEngine.__init__(map_seed, history_seed, n_cells, n_nations, ...)
```
1. `generate_world(map_seed, history_seed, n_cells, n_nations)` → `WorldState`
2. Create `LLMClient` (auto-detects provider from env vars)
3. Create `ContextManager` (memory system, max_user_tokens=4200)
4. For each nation:
   - Assign `GlobalStrategy` (rotation: EXPANSIONISM, ISOLATIONISM, COALITION_BUILDER, SCORCHED_EARTH)
   - Assign `GovernmentType` (rotation: DEMOCRACY, AUTHORITARIAN, THEOCRACY)
   - Create `NationAgent(nation_id, world, llm_client, strategy, context_manager, government_type)`
   - Allocate initial nukes based on strategy profile (SCORCHED_EARTH gets more)
5. Create `ActionEngine(world, spatial_manager)`
6. Initialize DB connections (SimulationDB, MetricsDB)

### 2.2 Turn Loop (7 Phases)

Each turn executes these phases in **strict sequential order**:

#### Phase 1: Scenario Injection
```python
# scenario_trigger = {"type": "PANDEMIA" | "SCOPERTA RISORSE" | "INSURREZIONE", "turn": T}
# Trigger turn is now fully configurable (UI slider or fork_and_continue argument).
# check_and_trigger_scenario() fires only when current_turn == trigger["turn"].
if trigger is not None:
    check_and_trigger_scenario(world, context_manager, current_turn, trigger)
```
Scenario effects:
- **PANDEMIA**: density-scaled mortality, military attrition, satisfaction penalty (food-weighted), global trust −10
- **SCOPERTA RISORSE**: selects a border province (4-tier priority), sets energy/materials to 50× world average
- **INSURREZIONE**: steals 25% of provinces from the least-stable nation, creates a rebel NationAgent with opposed government type

#### Phase 2: Upkeep (`phases.upkeep_phase`)
```python
for each active nation:
    1. Tax Collection: budget += Σ(province.tax_revenue)
    2. Production: food/energy/materials += production × unified_multiplier
       - unified_multiplier = workforce_mult × satisfaction_mult × energy_mult
    3. Consumption: food -= pop × 1.0, energy -= pop × 0.5 + military_energy
       - materials -= Σ(unit_maintenance_costs)
       - budget -= Σ(unit_salary_costs)
    4. Resource Capping: max_stock = 10 × consumption (prevent unlimited hoarding)
       - if stock > max_stock: stock = max_stock (spoilage)
    5. Crisis: if food < 0 → starvation (up to 10% pop/turn)
              if energy < 0 → production penalty (up to -50%)
```

#### Phase 3: Diplomacy Cleanup
```python
clear_expired_proposals(world)  # Remove proposals older than 1 turn
```

#### Phase 4: Agent Decision + Execution
```python
for each active nation:
    envelope = nation_agent.act(turn, injections)
    # Inside NationAgent.act():
    #   1. Ministers propose concurrently (async LLM calls)
    #   2. President reviews CabinetBriefing (sync LLM call)
    #   3. Build CountryEnvelope from PresidentialDecree
    
    action_engine.execute(envelope)
    # Inside ActionEngine:
    #   execute_defense_waterfall(payload)  # Priority-ordered
    #   execute_economic(payload)           # Single action
    #   execute_foreign(payload)            # Single action
    
    behavior_tracker.log_turn(envelope)
    metrics_db.save_metrics(extract_nation_metrics(world, envelope, turn))
```

#### Phase 5: Ambiguity Penalty
```python
for each envelope:
    if public_intent == IDLE and private_intent != IDLE:
        trust[sender] -= 2  # Penalize bluffing
```

#### Phase 6: Context Update
```python
context_manager.update_after_turn(turn, envelopes, world)
# Updates: relationships, extracts events, logs actions, presidential feedback
```

#### Phase 7: Opinion Phase (`phases.opinion_phase`)
```python
for each active nation:
    events = get_relevant_events(nation_id)
    gov_actions = get_government_actions(nation_id)
    
    opinion_response = opinion_agent.react(events, gov_actions, satisfaction, at_war)
    # Returns: multiplier_increase (0.1-2.0), multiplier_decrease (0.1-2.0)
    
    delta = calculate_turn_satisfaction_delta(nation, world, events, gov_actions, at_war)
    # Applies LLM multipliers to positive/negative components
    
    nation.public_satisfaction = clamp(0, 100, satisfaction + delta)
    check_triggers(nation)  # STRIKE, CIVIL_UNREST, RECOVERY
```

### 2.3 State Forking — Unified Fork & Continue

All forking flows (XAI injection and scenario) share the same engine primitives.

#### Snapshot Turn Semantics (critical for correct fork offset)
```
snapshot(T)  = world state AFTER turn T-1 has fully executed
             = world state AT THE START of turn T (before any agent acts on T)

load_state(T) → world.turn == T  (T is the NEXT turn to execute)
```

**Example**: Fork at snapshot T=10 → agents have acted through turn 9 → next execution is turn 10.

#### Primitive: `fork()`
```python
sim.fork(new_name=None)  # → new_simulation_id
# 1. Creates new simulation entry in DB
# 2. Copies full history (snapshots, envelopes, behaviors, token_usage) up to current_turn
# 3. Switches engine to new_simulation_id — subsequent steps persist to the fork
```

#### Primitive: `load_state(turn, from_simulation_id=None)`
```python
sim.load_state(T, from_simulation_id=source_id)
# 1. Loads WorldState from snapshot(T)
# 2. Reconstructs ContextManager memory
# 3. Re-initializes ActionEngine and Agents from restored WorldState
# 4. Reconstructs envelope trace_history for XAI dashboard
# Result: world.turn == T → NEXT turn to execute is T
```

#### High-Level: `fork_and_continue()` (unified XAI + Scenario)
```python
new_id = sim.fork_and_continue(
    source_simulation_id = source_id,
    fork_at_turn         = T,           # Load snapshot(T) → next exec. is T
    n_turns              = None,        # Auto: max_turn(source) - T; or explicit override
    injections           = [...],       # XAI: constraint list forwarded to every step()
    scenario_trigger     = {"type": "PANDEMIA", "turn": T+k},  # Scenario: fires at exact turn
    new_name             = "Fork @T10" # Optional friendly name
)
```

| Parameter | XAI path | Scenario path |
|-----------|----------|---------------|
| `injections` | Agent prompt constraints forced each turn | `[]` / `None` |
| `scenario_trigger` | `None` | `{"type": ..., "turn": T+k}` |
| `n_turns` | Auto: `max_turn(source) - fork_at_turn` | Same (or explicit cap) |

UI (Analysis mode sidebar) calls this via the session-state flow:
1. User time-travels to turn T (`load_state(T)`)
2. User configures injections and/or scenario trigger and trigger turn
3. Button computes `fork_remaining = max_turn(source) - world.turn` and calls `fork_and_continue()`

---

## 3. Cognitive Layer — Agent Architecture

### 3.1 NationAgent (`agents/nation_agent.py`, 484 lines)

```python
class NationAgent:
    def act(self, turn, injections=None) -> CountryEnvelope:
        # 1. CABINET PHASE (concurrent)
        defense_proposal, economy_proposal, foreign_proposal = \
            await _async_cabinet_phase(turn, def_inj, eco_inj, for_inj)
        
        briefing = CabinetBriefing(defense, economy, foreign)
        
        # 2. PRESIDENTIAL DECISION (sequential)
        decree = _presidential_decision(turn, briefing, injections)
        # PresidentialDecree: {defense: APPROVE/VETO, economy: APPROVE/VETO, ...}
        
        # 3. ENVELOPE CONSTRUCTION
        envelope = _construct_envelope_from_decree(turn, decree, briefing)
        # VETO → IDLE payload (no resource spending)
        # APPROVE → minister's payload with president's public_statement
        
        return envelope  # Contains full prompt traces for XAI
```

### 3.2 Minister Architecture (`agents/ministers.py`, 335 lines)

```python
class BaseMinister:
    def propose(self, strategy, turn, injection=None):
        # 1. Generate system prompt (cached across turns)
        system_prompt = self.prompt_class.build(nation_id, world, strategy, gov_type)
        
        # 2. Generate input prompt (dynamic each turn)
        input_prompt = self.input_builder.build(nation_id, world, turn, context_manager)
        
        # 3. Inject memory context (events, actions, presidential feedback)
        input_prompt = self._add_memory_context(input_prompt, domain)
        
        # 4. Inject XAI override (if present)
        if injection:
            input_prompt += f"\n\n⚠️ OVERRIDE: {injection}"
        
        # 5. LLM call with structured output validation
        response = llm_client.query_agent(system_prompt, input_prompt, ProposalSchema)
        
        return Proposal(intent=response.intent, payload=response.payload)
```

### 3.3 CountryEnvelope Structure

```
CountryEnvelope (~100 fields):
├── Strategic Layer
│   └── global_strategy: GlobalStrategy (EXPANSIONISM/ISOLATIONISM/COALITION/SCORCHED)
├── Public Layer (visible to all nations)
│   ├── public_statement: str
│   ├── defense_public_intent: DefenseIntentType
│   └── foreign_public_intent: ForeignIntentType
├── Private Layer (hidden, for XAI analysis only)
│   ├── defense_private_intent: DefenseIntentType
│   ├── foreign_private_intent: ForeignIntentType
│   └── reasoning: str (per domain)
├── Action Layer (ground truth for execution)
│   ├── defense_payload: DefensePayload (waterfall actions)
│   ├── economic_payload: EconomicPayload (single action)
│   └── foreign_payload: ForeignPayload (single action)
├── Trace Layer (for XAI prompt review)
│   ├── president_system_prompt, president_input_prompt, president_raw_json
│   ├── defense_system_prompt, defense_input_prompt, defense_raw_json
│   ├── economy_system_prompt, economy_input_prompt, economy_raw_json
│   ├── foreign_system_prompt, foreign_input_prompt, foreign_raw_json
│   └── opinion_system_prompt, opinion_input_prompt, opinion_raw_json
└── Original Proposals (for metrics extraction)
    ├── original_defense_proposal: DefenseProposal
    ├── original_economic_proposal: EconomicProposal
    └── original_foreign_proposal: ForeignProposal
```

### 3.4 Intent Types

**DefenseIntentType**: `DETERRENCE`, `CONQUEST`, `DEFENSE`, `IDLE`, `EXPORT_DEMOCRACY` (Democracy only), `HOLY_WAR` (Theocracy only)

**ForeignIntentType**: `COOPERATION`, `COERCION`, `APPEASEMENT`, `IDLE`, `EXPORT_DEMOCRACY` (Democracy only), `DIVINE_MANDATE` (Theocracy only)

**GovernmentType** affects available intent types and narrative framing but not mechanical rules.

### 3.5 ContextManager — Bounded Rationality

**File**: `agents/context/events/context_manager.py` (1058 lines)

```
ContextManager:
├── Relationships: Dict[str, Dict[str, RelationshipSummary]]
│   Each pair tracks: status (PEACE/WAR/ALLIANCE), trust, trend (↑↓→), events
├── Events: List[NotableEvent]
│   Types: MILITARY, DIPLOMATIC, ECONOMIC, CRISIS, NARRATIVE
│   Newsworthy outcomes only (internal proposals ≠ events)
├── Actions: Dict[str, List[MyAction]]
│   Per-nation action history with descriptive summaries
├── Presidential Feedback: Dict[str, List[Decision]]
│   Past APPROVE/VETO decisions per domain per nation
└── Pruning: max_user_tokens=4200
    Removes oldest events and actions when budget exceeded
```

---

## 4. Simulation Physics Layer — Action Execution

### 4.1 Defense Waterfall (`actions/defense/handler.py`, 985 lines)

Actions are sorted by `priority` field and executed sequentially. If an action fails validation, execution continues to next action.

```python
def execute_defense_waterfall(engine, nation_id, payload):
    sorted_moves = sorted(payload.moves, key=lambda m: m.priority)
    for move in sorted_moves:
        match move.action_type:
            case NUCLEAR_OPTION: _execute_nuclear_option(engine, nation_id, move)
            case MOVE_TROOPS:    _execute_move_troops(engine, nation_id, move)
            case CREATE_UNIT:    _execute_create_unit(engine, nation_id, move)
```

### 4.2 Combat Resolution (`actions/defense/combat.py`, 514 lines)

**Force Calculation**:
```
Force = soldiers × 1.0 + navy × 10.0 + aircraft × 5.0
Defender gets terrain_modifier bonus (MOUNTAIN = 1.5x)
```

**Binary Outcomes** (deterministic with RNG seed):
- **Land Combat**: `resolve_land_combat()` — attacker wins → conquers province, loses → all soldiers destroyed. Undefended provinces captured automatically.
- **Naval Combat**: `resolve_naval_combat()` — winner destroys all enemy ships.
- **Air Strike**: `resolve_air_strike()` — win = destroy defenders, lose = lose all aircraft. Air strikes cannot conquer territory.
- **Naval Landing** (5-stage flow):
  1. Check for enemy navy in water cell → naval combat
  2. Find adjacent coastal province
  3. If defenders → land combat
  4. Otherwise → auto-land
  5. Navy destroyed, crew converts to soldiers (10 per ship)

**Province Conquest** (`_conquer_province`):
- Transfer ownership, update province_ids
- Check if entire nation conquered (all provinces lost)
- If nation falls: mark as inactive, log event to ContextManager, annex remaining resources
- Clean up: ghost troops, pending proposals, trust data

### 4.3 Nuclear Effects
```python
def _execute_nuclear_option(engine, nation_id, move):
    target_province.population *= 0.1       # 90% death
    target_province.food_production *= 0.2  # 80% destroyed
    target_province.energy_production *= 0.2
    target_province.materials_production *= 0.2
    target_province.soldiers = 0            # All military eliminated
    target_province.aircraft = 0
    target_province.navy = 0
    trust[attacker → victim] = 0            # Zero trust
    for other_nation:
        trust[other → attacker] -= 80       # Global pariah (0-100 scale)
```

### 4.4 Economy Formulas

**Welfare Investment** (logarithmic diminishing returns):
```
Gain = WELFARE_MULTIPLIER × log(1 + Amount / 500)
WELFARE_MULTIPLIER = 7
WELFARE_MAX_BUDGET_RATIO = 0.25 (max 25% of current budget)
WELFARE_MATERIALS_RATIO = 0.20 (20% materials cost)
```

**War Tax**:
```
budget += population × 0.01
satisfaction -= 15 (scaled to -22 if satisfaction < 30)
Requires: satisfaction ≥ 20
```

**Trade Oracle**:
```
TradeScore = (E_val × M_scarcity) - (R_risk × P_projection)
Stock cap: max 15% of sender's current stock per resource
Accepted if score > threshold (based on trust level)
```

### 4.5 Satisfaction Dynamics

**Production Multiplier** (from `opinion/handler.py`):
```python
if satisfaction >= THRESHOLD_FULL_PRODUCTION (60):
    return 1.0
elif satisfaction >= THRESHOLD_PRODUCTION_DECAY_FLOOR (0):
    # Linear decay from 1.0 to MIN_PRODUCTION_MULTIPLIER
    return MIN_PRODUCTION + (1.0 - MIN_PRODUCTION) × (satisfaction / 60)
else:
    return MIN_PRODUCTION_MULTIPLIER
```

**Triggers**:
| Trigger | Condition | Effect |
|---------|-----------|--------|
| GENERAL_STRIKE | satisfaction < 20 | Production × 0.7, strike flag |
| CIVIL_UNREST | satisfaction < 10 | Production = 0, random province revolts |
| RECOVERY | satisfaction > 50 | Clear unrest/strike flags |

---

### 4.6 World Generation — Voronoi Pipeline

```python
class MapGenerator:
    def generate(self, history_seed):
        # Stage 1: Voronoi geometry
        vor, n_survivors = generate_voronoi(rng, n_cells=1500, relaxation_steps=3)
        adjacency = build_adjacency(vor, n_survivors)
        
        # Stage 2: Geography (land/ocean classification)
        land, ocean, centroids, vertices = generate_geography(vor, n_survivors, rng)
        
        # Stage 3: Nation placement (maximin distance selection)
        nations_dict, seed_ids = assign_nations(land, rng, n_nations=10)
        political_map = assign_provinces_to_nations(land, centroids, nations_dict, seed_ids)
        
        # Stage 4: Province creation (terrain-dependent initialization)
        provinces = create_provinces(land, ocean, political_map, adjacency, centroids, vertices, rng)
        
        # Stage 5: Territorial waters
        assign_territorial_waters(ocean, provinces, nations_dict)
        
        # Stage 6: Nation aggregates + stockpiles
        _calculate_nation_aggregates(nations_dict, provinces)
        # Stockpile = consumption × AUTONOMY_TURNS(5) × prosperity_factor(0.7-1.3)
        
        # Stage 7: Assemble WorldState
        world = WorldState(turn=1, provinces=provinces, nations=nations_dict, trust_matrix={})
        
        # Stage 8: Genesis (50-year historical simulation)
        genesis = GenesisEngine(world, seed=history_seed)
        genesis.initialize_history(years=50)
```

### 4.7 GenesisEngine (`world/genesis.py`, 311 lines)

Per-year simulation for each nation pair:
```
1. Trust decay: trust[a→b] -= TRUST_DECAY(0.02)
2. Border dynamics: if shared_border → friction → trust -= 5 to 15
3. Trade dynamics: if complementary_resources → trust += 3 to 8
4. Diplomatic shifts:
   - trust < 30 → rivalry event
   - trust > 70 → alliance event
   - trust > 80 → border dispute resolution
```

### 4.8 SpatialManager (`world/spatial/manager.py`, 176 lines)

Wraps \`NetworkX.Graph\` built from province adjacency:

```python
class SpatialManager:
    def get_permitted_path(self, from_id, to_id, nation_id, permitted_owner_ids, unit_type):
        # Creates subgraph of permitted nodes:
        # - Own territory: always permitted
        # - Allied territory: permitted if in permitted_owner_ids
        # - Start/end: always permitted (to allow attack targeting)
        # - Terrain constraints: no SOLDIER on OCEAN, no NAVY on land
        # - VOID terrain: always blocked
        # Returns shortest path through permitted subgraph, or None
```

---

## 5. Observability Layer — Persistence

### 5.1 SimulationDB Schema (`db/connection.py`, 430 lines)

```sql
CREATE TABLE simulations (
    simulation_id INTEGER PRIMARY KEY,
    name VARCHAR, genesis_seed INTEGER, simulation_seed INTEGER,
    n_cells INTEGER, n_nations INTEGER, scenario_json VARCHAR,
    created_at TIMESTAMP, forked_from INTEGER
);

CREATE TABLE snapshots (
    simulation_id INTEGER, turn INTEGER,
    provinces_json VARCHAR, nations_json VARCHAR,
    trust_matrix_json VARCHAR, relationship_matrix_json VARCHAR,
    world_events_json VARCHAR, memory_json VARCHAR,
    PRIMARY KEY (simulation_id, turn)
);

CREATE TABLE envelopes (
    simulation_id INTEGER, turn INTEGER, nation_id VARCHAR,
    envelope_json VARCHAR,
    PRIMARY KEY (simulation_id, turn, nation_id)
);

CREATE TABLE behaviors (
    simulation_id INTEGER, turn INTEGER, nation_id VARCHAR,
    deception_total FLOAT, deception_defense FLOAT, deception_foreign FLOAT,
    coherence_score FLOAT, global_strategy VARCHAR, government_type VARCHAR
);

CREATE TABLE token_usage (
    simulation_id INTEGER, turn INTEGER, nation_id VARCHAR,
    agent_type VARCHAR, prompt_tokens INTEGER, completion_tokens INTEGER,
    total_tokens INTEGER, model VARCHAR, cost FLOAT
);
```

### 5.2 MetricsDB Schema (`db/metrics_db.py`)

```sql
CREATE TABLE nation_metrics (
    simulation_id INTEGER, turn INTEGER, nation_id VARCHAR,
    deception_overall FLOAT, deception_defense FLOAT, deception_foreign FLOAT,
    coherence_score FLOAT,
    budget FLOAT, food FLOAT, energy FLOAT, materials FLOAT,
    population INTEGER, workers INTEGER, public_satisfaction FLOAT,
    in_civil_unrest BOOLEAN,
    soldiers INTEGER, aircraft INTEGER, navy INTEGER,
    power_projection FLOAT, trade_volume FLOAT, military_spending FLOAT
);

-- Global per-turn aggregates
CREATE TABLE global_metrics (
    simulation_id INTEGER, turn INTEGER,
    global_deception_avg FLOAT, global_coherence_avg FLOAT,
    global_satisfaction_avg FLOAT,
    territories_changed_hands INTEGER, units_created INTEGER,
    units_destroyed INTEGER, global_trade_volume FLOAT
);

-- Bilateral trust between all active nation pairs
CREATE TABLE trust_metrics (
    simulation_id INTEGER, turn INTEGER,
    observer_id VARCHAR, target_id VARCHAR,
    trust_value FLOAT, relationship_state VARCHAR
);

-- Engine-level acceptance/rejection per individual action (new)
CREATE TABLE metrics_action_outcomes (
    simulation_id INTEGER, turn INTEGER, nation_id VARCHAR,
    domain VARCHAR,       -- "Defense" | "Economy" | "Foreign"
    action_type VARCHAR,  -- specific action name
    status VARCHAR,       -- "SUCCESS" | "FAILED" | "PARTIAL" | "PENDING"
    reason VARCHAR        -- engine-provided rejection reason (if FAILED)
);

-- Presidential APPROVE/VETO decisions per domain (new)
CREATE TABLE metrics_presidential_decisions (
    simulation_id INTEGER, turn INTEGER, nation_id VARCHAR,
    domain VARCHAR,           -- "Defense" | "Economy" | "Foreign"
    decision VARCHAR,         -- "APPROVE" | "VETO"
    action_type VARCHAR,      -- proposed action type
    private_reasoning VARCHAR -- president's internal rationale
);
```

Populated per turn via `metrics.py` extractors called inside `_persist_envelopes()`.

### 5.3 Serialization (`db/serialization.py`, 8.9KB)

Handles complex type conversion:
- Pydantic models → JSON via `.model_dump()`
- Enums → string values
- Nested dicts (trust_matrix, relationship_matrix) → JSON strings
- WarStats, pending_proposals → serialized structures
- Deserialization reconstructs full Pydantic models from JSON

---

### 5.4 Deception Matrices

**Defense Matrix** (30+ entries):
```
(CONQUEST, DEFENSE)    = 0.9   # Classic deception
(CONQUEST, IDLE)       = 0.95  # Sneak attack preparation
(CONQUEST, EXPORT_DEMOCRACY) = 0.95  # Democracy moral washing
(CONQUEST, HOLY_WAR)   = 0.95  # Theocracy moral washing
(COERCION, COOPERATION)= 0.85  # Backstabbing (Foreign matrix)
(IDLE, CONQUEST)       = 0.8   # Bluff
```

**Aggregation**: `total = (defense_score + foreign_score) / 2.0`
Economic domain excluded — actions are directly observable.

### 5.5 Coherence Scoring

```python
EXPECTED_INTENTS = {
    TOTAL_EXPANSIONISM: (
        [CONQUEST, DETERRENCE, EXPORT_DEMOCRACY, HOLY_WAR],
        [COERCION, EXPORT_DEMOCRACY, DIVINE_MANDATE]
    ),
    ARMED_ISOLATIONISM: ([DEFENSE, DETERRENCE], [IDLE, APPEASEMENT]),
    COALITION_BUILDER: ([DEFENSE, DETERRENCE], [COOPERATION, COERCION, APPEASEMENT]),
    SCORCHED_EARTH: ([CONQUEST, DEFENSE, DETERRENCE, HOLY_WAR], [COERCION, DIVINE_MANDATE]),
}
# Score = matches / 2.0 (defense + foreign domains)
```

### 5.6 Divergence Analysis

```python
class DeltaAnalyzer:
    @staticmethod
    def calculate_divergence_score(base, fork) -> float:
        # Per-nation: |ΔSatisfaction| × 1.0 + |ΔPower| × 0.1
        # Global: ΔTrust × 0.5 + #RelationshipChanges × 50.0
        
    @staticmethod
    def explain_divergence(base, fork, client, injection_description) -> str:
        # LLM-powered: "Given injection X at turn T, why did delta Y occur?"
        # Uses DivergenceExplanation Pydantic model for structured response
```

---

## 6. Cross-Cutting Concerns

### 6.1 Prompt Architecture

```
agents/context/
├── system/          # Static persona + rules + action catalog
│   ├── president.py # "You are the Supreme Leader..."
│   ├── defense.py   # Available units, terrain, combat rules
│   ├── economy.py   # Welfare formula, trade constraints
│   ├── foreign.py   # Alliance tiers, message types
│   └── opinion.py   # Cultural traits, satisfaction context
├── input/           # Dynamic world state → natural language
│   ├── president.py # CabinetBriefing summary
│   ├── defense.py   # Military deployment map, border threats
│   ├── economy.py   # Resource balances, trade opportunities
│   ├── foreign.py   # Trust matrix, relationship states, proposals
│   └── opinion.py   # Events, government actions, current satisfaction
├── events/          # Memory management (ContextManager)
├── spatial.py       # Voronoi geography → text descriptions
├── military.py      # Military deployment → frontline analysis (34KB)
└── tokens.py        # Token counting and budget validation
```

### 6.2 LLM Client (`agents/llm_client.py`, 578 lines)

```python
class LLMClient:
    # Auto-detects provider from env vars:
    # AZURE_API_KEY → Azure OpenAI
    # ANTHROPIC_API_KEY → Claude (with prompt caching)
    # GROK_API_KEY → Grok-4
    # DEEPSEEK_API_KEY → DeepSeek-V3
    
    def query_agent(self, system_prompt, user_prompt, response_model, max_retries=3):
        # Uses Instructor for structured output validation
        # Uses LiteLLM for model abstraction
        # Automatic retry with exponential backoff
        # Captures raw content for XAI traces
        # Logs token usage via token_logger singleton
```

### 6.3 Token Observability

Every LLM call logs:
```
TokenUsageEntry:
    timestamp, turn, nation_id, role (President/DefenseMinister/etc),
    model, input_tokens, output_tokens, total_tokens, reasoning_tokens
```
Accumulated in-memory → flushed to CSV at simulation end.
Also persisted per-call in SimulationDB.token_usage table.

---

## 7. Package Dependency Graph

```
simulation/
├── depends on: agents/, actions/, calculators/, schemas/, world/, db/, analysis/
│
agents/
├── depends on: schemas/, actions/ (for payload types)
│   └── context/ depends on: schemas/, world/spatial
│
actions/
├── depends on: schemas/, calculators/, world/spatial (for pathfinding)
│
calculators/
├── depends on: schemas/ (WorldState, NationState for type hints)
│
world/
├── depends on: schemas/, calculators/ (for initial aggregates)
│
analysis/
├── depends on: agents/schemas (for CountryEnvelope, IntentTypes)
│   └── comparison depends on: schemas/, agents/ (LLMClient for explanations)
│
db/
├── depends on: schemas/ (for serialization targets)
│
schemas/
└── ZERO external dependencies (foundation layer)
```