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

## 👥 FASE 6: Public Opinion & Internal Stability
**Obiettivo:** Popolazione come vincolo al potere.

- [ ] 6.1 Satisfaction Dynamics (INVEST_WELFARE, RAISE_WAR_TAX)
- [ ] 6.2 Negative Triggers (GENERAL_STRIKE, CIVIL_UNREST)
- [ ] 6.3 Positive Triggers (RALLY_EFFECT)

---

## 🔍 FASE 7: Explainability (XAI)
**Obiettivo:** Tracciabilità e Controfattuali.
- [ ] 7.1 Structured Logger (Cabinet Debate)
- [ ] 7.2 Counterfactual Engine (Forking)
- [ ] 7.3 Query Interface ("Why did you do X?")

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