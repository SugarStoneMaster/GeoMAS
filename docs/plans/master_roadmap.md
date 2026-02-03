# 🗺️ GeoMAS Master Roadmap

## 🌍 FASE 1: The World Engine (Spatial & Physics)
**Status:** ✅ COMPLETATA
- [x] 1.1 Modelli Pydantic (`schemas/world.py`)
- [x] 1.2 Generazione Mappa Voronoi (`world_engine.py`)
- [x] 1.3 Grafo di Adiacenza NetworkX (`spatial_manager.py`)
- [x] 1.4 Deterministic Rules Oracle (Base)
- [x] 1.5 Genesis Module (Init History)

---

## 🧠 FASE 2: The Cognitive Layer (Agents)
**Status:** ✅ COMPLETATA
- [x] 2.1 Definizione Schemi Cognitivi (`protocol.py`).
- [x] 2.2 Struttura Agente (Presidente + Ministri).
- [x] 2.3 Integrazione LLM (Instructor/LiteLLM).
- [x] 2.4 Prompt Engineering & Context Injection.

---

## ✅ FASE 3: Advanced Resource & Economic Model
**Status:** ✅ COMPLETATA
- [x] Schema Updates (ProvinceState, NationState)
- [x] World Engine Updates (Territorial Waters, Nukes, Production)
- [x] Resource Consumption Logic (`economy.py`)
- [x] Trade Oracle (`trade_oracle.py`)
- [x] Action System Updates (INVEST_WELFARE, RAISE_WAR_TAX, TRADE_PROPOSAL)
- [x] Tests (66 test passati)

---

## 🛠️ FASE 3.5: Heavy Refactoring
**Status:** ✅ COMPLETATA
- [x] Rimozione codice legacy non più utilizzato
- [x] Riorganizzazione moduli e package
- [x] Pulizia schemi e deprecazioni (rimosso MinisterialState)
- [x] Documentazione inline e docstrings
- [x] Spostato `genesis.py` in `geomas/world/`

---

## 🖥️ FASE 3.6: Dashboard & UI Refactoring
**Status:** ✅ COMPLETATA
- [x] Refactoring `web/app.py` in moduli (components/, views/)
- [x] Layout 3-colonne (Stats | Map | Intel)
- [x] Controlli spostati in alto (no sidebar)
- [x] Trust Matrix sotto la mappa
- [x] Visualizzazione acque territoriali (blend colore + pattern)
- [x] Highlight nazione selezionata (bordi oro + desaturazione altre)
- [x] Formato numeri italiano (14.000)
- [x] Test UI (`tests/web/test_ui.py`)
- [x] 71 test totali passati

---

## 🪖 FASE 4: Advanced Military System
**Obiettivo:** Implementare unità militari, movimento, combattimento e nucleare.

### 4.1 Unit Types & Placement
- [x] **Definire `UnitType` Enum:** `SOLDIER`, `NAVY`, `AIRCRAFT`
- [x] **Vincoli di posizionamento:**
  - Soldiers/Aircraft: LAND, COASTAL, MOUNTAIN (no OCEAN)
  - Navy: Solo OCEAN (in acque territoriali)
  - Soldiers su Navy: max 100 uomini per nave

### 4.2 CREATE_UNIT Action
- [x] **Checks:** Possesso provincia, Budget, Materials, Popolazione
- [x] **Costi:** Upfront + Mantenimento
- [x] **Conversione popolazione → soldato**

### 4.3 MOVE_TROOPS Action
- [x] **Via terra/mare/aerea**
- [x] **Costo Energy**
- [x] **Logica destinazione:** Rinforzo vs Battaglia

### 4.4 Combat Resolution
- [x] **Formula danno** con moltiplicatore terreno
- [x] **Forza combinata alleanze**
- [x] **Penalità reputazione** se guerra non dichiarata
- [x] **Naval Landing (sbarco anfibio unificato):**
  1. Nave → acqua territoriale nemica
  2. Navi nemiche? → duello nave vs navi → sbarca su costa random
  3. No navi, unità su costa? → duello nave vs difensori → sbarca lì
  4. Nessuno? → sbarco automatico su costa random
  5. Sempre: nave distrutta, soldati = population nave

### 4.5 NUCLEAR_OPTION Action
- [x] **Distribuzione iniziale nukes** (seed-based)
- [x] **Effetti devastanti** (risorse → 0, Trust → 0)
- [x] **Diplomatic Fallout** (trust -0.8 per tutti)

---

## 🤝 FASE 5: Diplomacy & Treaty System
**Obiettivo:** Trattati, alleanze, guerra e pace.

- [x] 5.1 Relationship States (PEACE, WAR, ALLIANCE)
- [x] 5.2 SEND_DIPLOMATIC_MESSAGE (Praise, Threat, Insult)
- [x] 5.3 PROPOSE_ALLIANCE
- [x] 5.4 DECLARATION_OF_WAR
- [x] 5.5 BREAK_TREATY
- [x] 5.6 REQUEST_PEACE

---

## 👥 FASE 6: Public Opinion & Internal Stability ✅
**Obiettivo:** Popolazione come vincolo al potere tramite LLM Agent.

### 6.1 Schema & Package ✅
- [x] Migrare `public_satisfaction`: 0.0-1.0 → 0-100
- [x] Creare package `geomas/actions/opinion/`
- [x] Campi: `multiplier_increase`, `multiplier_decrease`, `cultural_traits`, `civil_unrest_active`
- [x] Campo `in_revolt: bool` in ProvinceState

### 6.2 Satisfaction Dynamics ✅
- [x] Base deltas: WAR -3, PEACE +1, deficit -2, surplus +1
- [x] Formula: `positive * mult_inc + negative * mult_dec`
- [x] **INVEST_WELFARE**: logaritmico `10 * log(1 + amount/100)`
- [x] **RAISE_WAR_TAX**: -15 satisfaction

### 6.3 Automatic Triggers ✅
- [x] **GENERAL_STRIKE**: sat < 20 → production -50%
- [x] **CIVIL_UNREST**: sat < 10 → 50% province revolt
- [x] Recovery: sat > 50 → provinces restored

### 6.4 Tests ✅
- [x] 18 test specifici per opinion system

### 6.5 Population LLM Agent (TODO)
- [ ] System prompt template con demographics + cultural traits (seed)
- [ ] Input: eventi turno, decisioni governo
- [ ] Output: multiplier_increase, multiplier_decrease (0.1-2.0)
- [ ] Vedi: `geomas/agents/opinion.py`

---

## 🔍 FASE 7: Explainability (XAI)
**Obiettivo:** Tracciabilità e Controfattuali.
- [ ] 7.1 Structured Logger (Cabinet Debate)
- [ ] 7.2 Counterfactual Engine (Forking)
- [ ] 7.3 Query Interface ("Why did you do X?")

---

## 🎭 FASE 7.5: Deception Detection Framework ✅
**Obiettivo:** Misurare la deception tra dichiarazioni pubbliche e intenzioni private.

### 7.5.1 Protocol Refactor ✅
- [x] Aggiungere `public_intent` e `private_intent` per ogni dominio (3+3)
- [x] Aggiungere `private_reasoning` per ogni dominio (XAI)
- [x] Mantenere `GlobalStrategy` per orientamento strategico
- [x] `public_statement` unico con sezioni defense/economy/foreign

### 7.5.2 Intent Enums Review ✅
- [x] Verificare `DefenseIntentType` sia completo
- [x] Verificare `EconomicIntentType` sia completo
- [x] Verificare `ForeignIntentType` sia completo

### 7.5.3 Deception Calculator ✅
- [x] Creare matrice deception per ogni dominio: `score(private, public)`
- [x] Implementare `DeceptionAnalyzer` in `geomas/analysis/deception.py`
- [x] Aggregare score per turno e per nazione

### 7.5.4 Behavior Tracker ✅
- [x] Struttura `BehaviorRecord` per logging
- [x] Tracciare per ogni turno: intents, actions, scores
- [x] Statistiche aggregate: media, max, trend

### 7.5.5 Strategic Coherence ✅
- [x] Mapping `EXPECTED_INTENTS[GlobalStrategy] -> intents tipici`
- [x] Implementare `CoherenceAnalyzer.calculate_score(strategy, private_intents)`
- [x] Due metriche indipendenti: Deception + Coherence

### 7.5.6 Dashboard Integration
- [ ] Visualizzare deception score per nazione
- [ ] Visualizzare coherence score per nazione
- [ ] Timeline nel tempo
- [ ] Dettaglio per dominio

---

## 💾 FASE 7.6: Persistence Layer & XAI Database
**Obiettivo:** Salvare stato simulazione per analisi post-hoc e explainability.
**Status:** ✅ Database Layer Complete, Context Management In Progress

### 7.6.1 Database Design ✅
- [x] DuckDB file-based OLAP database
- [x] Schema: simulations, snapshots, envelopes, behaviors
- [x] Package `geomas/db/` con SimulationDB class

### 7.6.2 World State Snapshots ✅
- [x] Salvare `WorldState` completo per ogni turno
- [x] Serializzazione/deserializzazione con gestione numpy types
- [x] `load_world_at_turn()` per ricostruire stato

### 7.6.3 Agent Decision Logs ✅
- [x] Salvare tutti i `CountryEnvelope` per turno
- [x] Auto-persist in SimulationEngine.step()

### 7.6.4 Behavior Metrics ✅
- [x] Persistere deception/coherence scores per turno
- [x] Query interface con DataFrame output

### 7.6.5 Context Management System (In Progress)
- [ ] Package `geomas/memory/` con ContextManager
- [ ] RelationshipSummary: pre-computed summaries per relazione
- [ ] NotableEvent: eventi significativi filtrati
- [ ] MyAction: cronologia azioni proprie (ego-centric)
- [ ] Token budget management (~5000 max)
- [ ] Pruning strategy per history overflow
- [ ] Integration con NationAgent prompts

---

## 📊 FASE 8: Simulation Loop & Validation
**Obiettivo:** Esecuzione scientifica.
- [ ] 8.1 Batch Running (Multi-seed)
- [ ] 8.2 Metriche di Stabilità e Coerenza

---

## 🔧 FASE 9: Dashboard Advanced
**Obiettivo:** Visualizzazione avanzata.
- [x] 9.1 Streamlit Dashboard (Base)
- [x] 9.2 Layout modulare e responsivo
- [x] 9.3 Visualizzazione acque territoriali
- [x] 9.4 Evidenziazione nazione selezionata
- [ ] 9.5 Frecce movimento truppe
- [ ] 9.6 Icone unità militari
- [ ] 9.7 Grafici storici (Trust/Budget nel tempo)