# 🚀 Sprint: Fase 7.6 - Persistence & Context

**Status:** In Progress | **Test:** 257 passati

---

## ✅ Completato

| Component | Files | Note |
|-----------|-------|------|
| **SimulationDB** | `geomas/db/connection.py` | DuckDB persistence |
| **TurnCache** | `geomas/db/cache.py` | In-memory cache ultimi N turni |
| **GenesisDB** | `geomas/db/genesis.py` | DB eventi storici |
| **SpatialTranslator** | `geomas/agents/context/spatial.py` | Geography, borders, encirclement |
| **MilitaryTranslator** | `geomas/agents/context/military.py` | Forces, threats, options |
| **NationProfileGenerator** | `geomas/agents/context/profile.py` | Identity, history, economy |
| **Prompt Architecture** | `geomas/agents/context/system/`, `input/` | 5 system + 5 input builders |
| **ContextManager** | `geomas/agents/context/memory/` | Schemas + memory management |

### Task Completati

- [x] Context Management Package (`schemas.py`, `context_manager.py`)
- [x] Memory Update Logic (`_update_relationships`, `_extract_events`, `_log_actions`, `_prune_if_needed`)
- [x] Context Output (`get_relationships_for`, `get_events_for`, `get_actions_for`)
- [x] Tests (15 test per memory, 22 per prompts)

---

## 🔜 TODO: Integration

### 11. SimulationEngine Integration
- [ ] Hook ContextManager in `SimulationEngine.__init__`
- [ ] Chiamare `context_manager.update_after_turn()` dopo ogni turno
- [ ] Chiamare `context_manager.initialize_from_world()` all'inizio

### 12. Agent Integration
- [ ] Modificare `NationAgent` per usare system prompts
- [ ] Modificare `NationAgent` per usare input builders
- [ ] Passare context da ContextManager agli InputBuilders

### 13. Token Counting (Optional)
- [ ] Implementare token counter (tiktoken o approximation)
- [ ] Validare budget compliance

---

## 📌 Reference: Token Budget

```
Per ogni agente (5000 token max):
├── SYSTEM (~800): Identità + GlobalStrategy + Regole output
└── INPUT (~4200): State + Relationships + Events + Actions
```

**Pruning**: MAX_EVENTS=50, MAX_ACTIONS_PER_DOMAIN=10, MAX_RELATIONSHIP_EVENTS=3