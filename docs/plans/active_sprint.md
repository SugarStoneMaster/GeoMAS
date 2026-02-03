# 🚀 Sprint: Fase 7.6 - Persistence Layer & XAI Database

**Status:** In Progress
**Obiettivo:** Salvare stato simulazione per analisi post-hoc e explainability

---

## ✅ Completato

### 1. Database Layer (DuckDB) ✅
- [x] Package `geomas/db/` con `SimulationDB`, serialization helpers
- [x] Schema: simulations, snapshots, envelopes, behaviors
- [x] Serializzazione/deserializzazione WorldState, Envelopes
- [x] Query interface: `load_world_at_turn()`, `get_behavior_timeline()`
- [x] SimulationEngine integration: auto-persist ogni turno
- [x] 16 test passati

### 2. In-Memory Cache ✅
- [x] `TurnCache` class in `geomas/db/cache.py`
- [x] Caching ultimi N turni (default 20)
- [x] O(1) access via `_turn_index` dict
- [x] Deep copy WorldState per evitare mutation
- [x] Auto-eviction oldest turns when at capacity
- [x] Integrato in `SimulationEngine` con `cache_size` parameter
- [x] Cache access methods: `get_cached_world()`, `get_cached_envelopes()`, etc.
- [x] 10 test passati (193 totali)

### 3. Genesis DB ✅
- [x] `GenesisDB` class in `geomas/db/genesis.py`
- [x] Schema: genesis_meta, events, initial_trust, alliances
- [x] `save_events_batch()` per bulk insert
- [x] Query: `get_events_for_nation()`, `get_events_by_tag()`
- [x] `GenesisEngine` integration con `db_path` parameter
- [x] Auto-persist eventi, trust matrix, e alliances
- [x] 9 test passati (202 totali)

---

## 🔜 In Corso: Context Management System

### Problema
Gli agenti LLM necessitano di context appropriato per decidere. Sfide:
1. **Token limit**: Max ~5000 token totali (system + user prompt)
2. **Relevance**: Includere info pertinenti senza sapere a priori con chi interagiranno
3. **History growth**: La storia cresce ma il budget token è fisso
4. **Ego-centric view**: Ogni nazione ha visione parziale del mondo

### Decisione: Hybrid B+E (Relationship Summaries + Event Memory)

```
┌─────────────────────────────────────────────────────────┐
│ TOKEN BUDGET (5000 max)                                 │
├─────────────────────────────────────────────────────────┤
│ SYSTEM PROMPT (statico)             ~800 token          │
│ ├── Personalità nazione                                 │
│ ├── GlobalStrategy                                      │
│ └── Regole output                                       │
├─────────────────────────────────────────────────────────┤
│ USER PROMPT (dinamico)              ~4200 token         │
│ ├── Current State (NationState)      ~300 token         │
│ ├── Relationship Summaries           ~1500 token        │
│ ├── Notable Events                   ~1000 token        │
│ ├── My Recent Actions                ~800 token         │
│ └── Instructions/Buffer              ~600 token         │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Schema Context Management

### RelationshipSummary (Opzione B)
Summary compatto di ogni relazione bilaterale. Pre-calcolato, aggiornato dopo ogni turno.

```python
class RelationshipSummary:
    other_nation_id: str
    other_nation_name: str
    
    # Stato corrente (dal world state)
    relationship: RelationshipState  # WAR, PEACE, ALLIANCE
    trust: float  # 0-100
    trust_trend: str  # "↑" rising, "↓" falling, "→" stable
    
    # Ultima interazione
    last_interaction_turn: Optional[int]
    last_interaction_summary: Optional[str]  # "They proposed alliance"
    
    # Eventi notevoli (max 2-3, più recenti)
    notable_events: List[str]  # ["T5: broke treaty", "T10: attacked us"]
    
    def to_prompt_line(self) -> str:
        """~30-50 token per relazione."""
        ...
```

**Budget**: ~150 token × 10 nazioni = ~1500 token

### NotableEvent (Opzione E)
Eventi significativi globali o che coinvolgono la nazione.

```python
class NotableEvent:
    turn: int
    event_type: EventType  # WAR_DECLARED, ALLIANCE_FORMED, ATTACK, TRADE_DEAL, CRISIS
    actors: List[str]  # Nazioni coinvolte
    summary: str  # "Valdoria attacked Aquilonia"
    relevance_to: Optional[str]  # None = globale, altrimenti nazione specifica
    
    def to_prompt_line(self) -> str:
        """~20 token per evento."""
        return f"Turn {self.turn}: {self.summary}"
```

**Budget**: ~20 token × 50 eventi = ~1000 token

### MyAction (Azioni proprie passate)
Ego-centric: ogni nazione vede solo le proprie azioni.

```python
class MyAction:
    turn: int
    domain: str  # "Defense", "Economy", "Foreign"
    action_summary: str  # "Attacked Province 7 of Valdoria"
    outcome: Optional[str]  # "Captured", "Failed", "Accepted"
    
    def to_prompt_line(self) -> str:
        """~25 token per azione."""
        ...
```

**Budget**: ~25 token × 30 azioni = ~750 token

---

## 📈 Token Scaling Over Time

| Turno | Token Usati | Note |
|-------|-------------|------|
| 1 | ~1500 | Minimal history |
| 10 | ~2500 | Relationships forming |
| 30 | ~4000 | Rich history |
| 50+ | ~4500 | Capped, oldest pruned |

### Pruning Strategy
Quando budget superato:
1. **Eventi**: Mantieni ultimi 30 + eventi critici (war/alliance)
2. **Azioni**: Mantieni ultime 10 per dominio
3. **Relationship Notable**: Mantieni ultimi 2 per relazione

---

## 🏗️ Architettura ContextManager

```python
class ContextManager:
    """Gestisce memoria e genera context per ogni agente."""
    
    def __init__(self, db: SimulationDB, max_user_tokens: int = 4200):
        self.db = db
        self.max_user_tokens = max_user_tokens
        
        # Memory stores (pre-computed, aggiornati dopo ogni turno)
        self.relationship_summaries: Dict[str, Dict[str, RelationshipSummary]] = {}
        self.global_events: List[NotableEvent] = []
        self.nation_actions: Dict[str, List[MyAction]] = {}
    
    def update_after_turn(
        self, 
        turn: int, 
        envelopes: List[CountryEnvelope], 
        world: WorldState
    ) -> None:
        """Aggiorna tutte le memorie dopo un turno."""
        self._update_relationships(world)
        self._extract_events(turn, envelopes)
        self._log_actions(turn, envelopes)
        self._prune_if_needed()
    
    def build_context_for(self, nation_id: str, world: WorldState) -> str:
        """Genera user prompt context per una nazione."""
        sections = [
            self._build_current_state(nation_id, world),
            self._build_relationships(nation_id),
            self._build_events(nation_id),
            self._build_my_actions(nation_id),
        ]
        return "\n\n".join(sections)
```

---

## 📋 Task Breakdown

### 8. Context Management Package
- [ ] Creare `geomas/memory/__init__.py`
- [ ] Creare `geomas/memory/schemas.py` (RelationshipSummary, NotableEvent, MyAction)
- [ ] Creare `geomas/memory/context_manager.py` (ContextManager class)

### 9. Memory Update Logic
- [ ] `_update_relationships()` - calcola trust trend, aggiorna summaries
- [ ] `_extract_events()` - identifica eventi notevoli da envelopes
- [ ] `_log_actions()` - registra azioni eseguite
- [ ] `_prune_if_needed()` - rispetta budget token

### 10. Context Building
- [ ] `_build_current_state()` - NationState → prompt section
- [ ] `_build_relationships()` - RelationshipSummary → prompt section
- [ ] `_build_events()` - filtra eventi rilevanti per nazione
- [ ] `_build_my_actions()` - formatta azioni passate

### 11. Integration
- [ ] Hook ContextManager in SimulationEngine
- [ ] Modificare NationAgent per usare ContextManager
- [ ] Token counting e validation

### 12. Tests
- [ ] Test RelationshipSummary generation
- [ ] Test event extraction
- [ ] Test pruning logic
- [ ] Test token budget compliance

---

## 📌 Formato Prompt Atteso

```
== YOUR CURRENT STATE ==
Budget: 1,500 | Soldiers: 5,000 | Aircraft: 200 | Navy: 50
Provinces: 8 land, 3 territorial waters
Resources: Food +10/turn, Energy +5/turn, Materials +8/turn
Nuclear: 2 warheads | Satisfaction: 65%

== YOUR RELATIONSHIPS ==
- Zephyria: ALLIANCE, Trust 85 (rising). Last: trade deal T20. History: T5: formed alliance
- Valdoria: WAR, Trust 12 (falling). Last: they attacked T24. History: T15: broke peace treaty
- Meridian: PEACE, Trust 55 (stable). Last: no recent contact. History: -

== RECENT WORLD EVENTS ==
Turn 24: Valdoria attacked Aquilonia's northern border
Turn 23: Meridian facing food crisis
Turn 22: Zephyria and Meridian signed trade agreement

== YOUR RECENT ACTIONS ==
Turn 24 [Defense]: Reinforced Province 12 with 500 soldiers
Turn 23 [Economy]: Proposed trade deal with Meridian → Accepted
Turn 22 [Defense]: Attacked Valdoria's Province 7 → Captured
```

---

## 📌 Notes
- System prompt statico (~800 token) contiene personalità + GlobalStrategy
- User prompt dinamico (~4200 token) generato da ContextManager
- Token budget cresce da ~1500 (turno 1) a ~4500 (turno 50+)
- Pruning automatico mantiene budget sotto limite
- Ispirato a WarAgent: Board + Stick + Past Actions pattern