# 🚀 Sprint: Fase 7.6 - Persistence & Context

**Status:** In Progress | **Test:** 290 passati

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
| **TokenCounter** | `geomas/agents/context/tokens.py` | tiktoken-based, budget validation |

### Task Completati

- [x] Context Management Package
- [x] Memory Update Logic
- [x] Context Output methods
- [x] Token Counter (tiktoken)
- [x] Prompt Budget Tests (19 test)
- [x] Realistic Budget Tests (7 test con ContextManager popolato)

### Token Budget Results

**Stress Test (20 nations, 25 events, 30 actions):**

| Component | Tokens |
|-----------|:------:|
| System | 500 |
| Base input | 400 |
| Relationships (19) | 646 |
| Events (25) | 425 |
| Actions (30) | 540 |
| **TOTAL** | **2511 (50%)** |

Budget confirmed safe for simulations up to 20 nations.

---

## ✅ Integration Complete

### 13. SimulationEngine Integration ✅
- [x] Hook ContextManager in `SimulationEngine.__init__`
- [x] Chiamare `context_manager.update_after_turn()` dopo ogni turno
- [x] Chiamare `context_manager.initialize_from_world()` all'inizio

### 14. Agent Integration ✅
- [x] Modificare `NationAgent` per usare system prompts
- [x] Modificare `NationAgent` per usare input builders
- [x] Passare context da ContextManager agli InputBuilders

### 15. Minister Integration ✅
- [x] DefenseMinister usa `DefenseSystemPrompt` + `DefenseInputBuilder`
- [x] EconomicMinister usa `EconomySystemPrompt` + `EconomyInputBuilder`
- [x] ForeignMinister usa `ForeignSystemPrompt` + `ForeignInputBuilder`
- [x] Tutti i ministri ricevono ContextManager per memoria

---

## 📌 Reference: Token Budget

```
Per ogni agente (5000 token max):
├── SYSTEM (~800): Identità + GlobalStrategy + Regole output
└── INPUT (~4200): State + Relationships + Events + Actions
```

**Pruning**: MAX_EVENTS=50, MAX_ACTIONS_PER_DOMAIN=10, MAX_RELATIONSHIP_EVENTS=3