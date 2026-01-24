# 🗺️ GeoMAS Master Roadmap

## 🌍 FASE 1: The World Engine (Spatial & Physics)
**Obiettivo:** Creare un mondo deterministico procedurale.
- [x] 1.1 Modelli Pydantic (`schemas/world.py`)
- [x] 1.2 Generazione Mappa Voronoi (`world_engine.py`)
- [x] 1.3 Grafo di Adiacenza NetworkX (`spatial_manager.py`)
- [x] 1.4 Deterministic Rules Oracle (Base)
- [x] 1.5 Genesis Module (Init History)

---

## 🧠 FASE 2: The Cognitive Layer (Agents)
**Obiettivo:** Implementare il Governo Neuro-Simbolico.
- [x] 2.1 Definizione Schemi Cognitivi (`protocol.py`).
- [x] 2.2 Struttura Agente (Presidente + Ministri).
- [x] 2.3 Integrazione LLM (Instructor/LiteLLM).
- [x] 2.4 Prompt Engineering & Context Injection.

---

## ⚙️ FASE 3: Advanced Resource & Economic Model
**Obiettivo:** Modellare un'economia realistica con risorse, popolazione e scarsità.

### 3.1 Resource System Refactoring
- [ ] **Estendere `ProvinceState`** con produzione risorse:
  - `food_production`, `energy_production`, `materials_production`
  - `tax_revenue` (per province)
- [ ] **Estendere `NationState`** con aggregati nazionali:
  - `total_food`, `total_energy`, `total_materials`, `total_budget`
  - `food_consumption`, `energy_consumption` (funzione della popolazione)
  - `materials_consumption` (funzione dell'esercito)

### 3.2 Population & Workforce Model
- [ ] **Popolazione come risorsa finita:**
  - Ogni provincia ha `population` (già esiste)
  - I soldati vengono "presi" dalla popolazione → meno lavoratori
  - Meno lavoratori = meno produzione di Food/Energy/Materials
- [ ] **Formule di produzione:**
  - `production = base_yield * (workers / max_workers)`

### 3.3 Trade Oracle (Deterministic Trade Acceptance)
- [ ] **Implementare la formula `TradeScore`:**
  ```
  TradeScore = (E_val × M_scarcity) - (R_risk × P_projection)
  ```
  - `E_val`: Valore economico base (Food=1, Energy=2, Materials=3)
  - `M_scarcity`: Moltiplicatore scarsità (1.0 → 5.0)
  - `R_risk`: Rischio relazionale da Trust Matrix
  - `P_projection`: Impatto su proiezione di forza
- [ ] **Trade accettato automaticamente se `TradeScore > 0`**

---

## 🪖 FASE 4: Advanced Military System
**Obiettivo:** Implementare unità militari, movimento, combattimento e nucleare.

### 4.1 Unit Types & Placement
- [ ] **Definire `UnitType` Enum:** `SOLDIER`, `NAVY`, `AIRCRAFT`
- [ ] **Estendere `ProvinceState`:**
  - `soldiers: int`, `aircraft: int`, `navy: int`
- [ ] **Estendere `NationState`:**
  - `total_soldiers`, `total_navy`, `total_aircraft`
  - `nukes: int` (nazionale, non per provincia)
- [ ] **Vincoli di posizionamento:**
  - Soldiers/Aircraft: LAND, COASTAL, MOUNTAIN (no OCEAN)
  - Navy: Solo OCEAN (in acque territoriali)
  - Soldiers su Navy: max 100 uomini per nave

### 4.2 Territorial Waters
- [ ] **Logica acque territoriali:**
  - Province OCEAN adiacenti a province COASTAL owned → owned
  - Aggiornare `map_engine.py` per assegnare ownership
  - Navy può stare solo in acque territoriali proprie o alleate

### 4.3 CREATE_UNIT Action
- [ ] **Checks:**
  - Possesso provincia
  - Budget sufficiente
  - Materials sufficienti
  - Popolazione sufficiente (per SOLDIER)
- [ ] **Costi:**
  - Upfront: Budget + Materials + Energy
  - Mantenimento: Materials per turno
  - Conversione popolazione → soldato

### 4.4 MOVE_TROOPS Action
- [ ] **Tipi di movimento:**
  - **Via terra:** Path tra province LAND/COASTAL/MOUNTAIN
  - **Via mare:** Navy trasporta soldati, consuma Energy × distanza
  - **Via aerea:** Range limitato, consuma Energy × distanza
- [ ] **Costo:** Energy = tipo_unità × distanza
- [ ] **Logica destinazione:**
  - Se B è alleata → Rinforzo
  - Se B è nemica → Battaglia

### 4.5 Combat Resolution
- [ ] **Formula danno:**
  ```
  Danni = Attacco - (Difesa × MoltiplicatoreTerreno)
  ```
  - MOUNTAIN: ×1.5 difesa
  - COASTAL: ×1.0
  - LAND: ×1.0
- [ ] **Forza combinata alleanze** (se alleanza attiva)
- [ ] **Penalità reputazione** se guerra non dichiarata
- [ ] **Impatto satisfaction** dopo tot morti

### 4.6 NUCLEAR_OPTION Action
- [ ] **Nukes a inizio partita:**
  - 2-3 nazioni con nukes (seed-based), le altre 0
  - Distribuzione casuale quantità
- [ ] **Effetti:**
  - Provincia target: risorse → 0, popolazione → 10%
  - Trust attaccante → 0 con TUTTI
  - **Coalition of Survival:** Se Trust(A,B) ≥ 0.50 → alleanza automatica contro aggressore nucleare
- [ ] **Costo:** 1 nuke consumata

---

## 🤝 FASE 5: Diplomacy & Treaty System
**Obiettivo:** Implementare trattati, alleanze, guerra e pace.

### 5.1 Relationship States
- [ ] **Definire `RelationshipStatus` Enum:**
  - `PEACE`, `WAR`, `ALLIANCE` (difensiva)
- [ ] **Matrice relazioni** oltre alla Trust Matrix

### 5.2 SEND_DIPLOMATIC_MESSAGE
- [ ] **Tipi:** Praise, Threat, Insult
- [ ] **Cooldown:** Non spammabile (1 messaggio per nazione per turno)
- [ ] **Effetto:** Modifica Trust (delta piccolo)
- [ ] **Warning:** Messaggi a nemici di alleati danneggiano trust con alleato

### 5.3 PROPOSE_ALLIANCE
- [ ] **Requisito:** Trust reciproco alto (≥0.75)
- [ ] **Accettazione automatica** se trust reciproco OK
- [ ] **Tipo:** Difensivo (mutual defense clause)
- [ ] **Obbligo:** Entrare in guerra se alleato attaccato → altrimenti BREAK_TREATY

### 5.4 DECLARATION_OF_WAR
- [ ] **Effetti:**
  - Status → WAR
  - Trust → 0 con target
  - Trust abbassata con alleati del target
  - Neutra con non-coinvolti
- [ ] **Bonus:** Riduce penalità reputazione vs attacco a sorpresa
- [ ] **Malus:** Perde elemento sorpresa, target ha 1 turno per prepararsi
- [ ] **Casus Belli:** (TODO: definire in futuro)

### 5.5 BREAK_TREATY
- [ ] **Effetti:**
  - Cancella alleanza
  - Crollo Trust con ex-alleato
  - Penalità reputazione globale
- [ ] **Permette:** Attacco ex-alleato stesso turno

### 5.6 REQUEST_PEACE
- [ ] **Condizioni:**
  - Invasore: deve offrire riparazioni (Budget)
  - Invaso: può offrire territori
  - Stallo: nessuna concessione
- [ ] **Se accettata:**
  - Status → PEACE
  - Truppe tornano a province di origine
- [ ] **Impatto satisfaction** (positivo)

---

## 👥 FASE 6: Public Opinion & Internal Stability
**Obiettivo:** Popolazione come vincolo realistico al potere del governo.

### 6.1 Satisfaction Dynamics
- [ ] **INVEST_WELFARE:**
  - Aumenta satisfaction (scala logaritmica)
  - Costo: Budget + Food
- [ ] **RAISE_WAR_TAX:**
  - Genera Budget massivo
  - Crollo satisfaction
  - Prerequisito: satisfaction ≥ 20%

### 6.2 Negative Triggers (Deterministici)
- [ ] **GENERAL_STRIKE (satisfaction < 30%):**
  - Province non producono Materials/Energy
  - Tasse al 50%
  - Costo movimento truppe ×2
- [ ] **CIVIL_UNREST (satisfaction < 10%):**
  - Probabilità diserzione militare ogni turno
  - Risorse saccheggiate random ogni turno
  - Solo difesa permessa, no attacco

### 6.3 Positive Triggers
- [ ] **RALLY_EFFECT (se attaccati/dichiarazione guerra ricevuta):**
  - Satisfaction non scende per X turni
  - Dopo X turni: sconto penalità satisfaction
  - Nuovi soldati non consumano budget

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

## 🖥️ FASE 9: Dashboard & Analysis
**Obiettivo:** Visualizzazione.
- [x] 9.1 Streamlit Dashboard (Base)
- [ ] 9.2 Visualizzazione avanzata (Frecce movimento, Icone unità)
- [ ] 9.3 Grafici storici (Trust/Budget nel tempo)
- [ ] 9.4 Pannello Acque Territoriali