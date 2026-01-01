# 👑 GeoMAS (Geopolitical Multi-Agent Simulation) - Implementation Plan v1.0

> **PRIMARY DIRECTIVE:** Questo non è un videogioco per intrattenimento. È un simulatore scientifico per una Tesi Magistrale.
> **Priorità Assolute:**
> 1. **Determinismo:** A parità di seed, la mappa e le decisioni devono essere identiche.
> 2. **Tracciabilità:** Ogni singolo cambio di stato deve essere loggabile e consultabile.
> 3. **Modularity:** Il codice deve essere diviso in moduli chiari per permettere l'inserimento futuro dell'Explainability Layer.
> 
> 

---

## 🛠 Tech Stack

* **Core:** Python 3.10+
* **Data Models:** `Pydantic` (Gestione rigida schemi JSON).
* **Spatial & Math:** `numpy`, `scipy.spatial` (Voronoi), `shapely` (Calcolo confini/aree), `scipy.optimize` (Per calcoli di utilità economica).
* **Graph:** `NetworkX` (Per gestire il grafo di adiacenza derivato dal Voronoi).
* **LLM Interface:** `LiteLLM` (Interfaccia agnostica) o `Instructor`.
* **Visualization & UI:** `Streamlit` (Dashboard web interattiva per analisi post-mortem e runtime), `Plotly` (Interattività), `matplotlib` (Debug).

---

## 🌍 FASE 1: Il "World Engine" Spaziale (The Body)

**Obiettivo:** Creare un mondo deterministico procedurale con geografia, risorse e fisica.

### Step 1.1: Definizione Modelli Pydantic (Gerarchici)

* **Task:** Creare `schemas.py`.
* **Dettagli:**
* `ProvinceState`: ID, OwnerID, TerrainType (Land/Ocean), ResourceValue (int), Coordinates (x,y).
* `NationState`: ID, Name, Color, List[ProvinceIDs], **MinisterialState** (Budget, Satisfaction, TechTree).
* `WorldMap`: Contiene i dati grezzi del Voronoi (vertices, regions) e il Grafo di Adiacenza (`adj_matrix`).
* `WorldState`:
* `map_data`: Oggetto `WorldMap`.
* `nations`: Dizionario delle nazioni.
* `turn_number`: Intero.
* **`trust_matrix`**: Matrice o dizionario che traccia la reputazione bilaterale (0.0 a 1.0) tra ogni coppia di nazioni **(Rif. Ramchurn et al.)**.
* **`active_treaties`**: Lista di trattati attivi con i loro modificatori numerici.





### Step 1.2: Map Generation (Voronoi & Tectonics)

* **Task:** Creare `map_engine.py`.
* **Logica da implementare:**
1. **Seed Generation:** Generare N punti random.
2. **Lloyd Relaxation:** Applicare 2-3 passaggi di smoothing per regolarizzare i poligoni.
3. **Tectonic Shaping:** Generare K centri continentali. Assegnare le province a "Land" o "Ocean" basandosi sulla distanza dai centri continentali + Noise.
4. **Nation Clustering:** Assegnare le capitali (random sampling su Land) e usare l'algoritmo Nearest Neighbor (basato sui centroidi) per assegnare ogni provincia alla nazione più vicina.
5. **Graph Construction:** Costruire un grafo `NetworkX` dove ogni Nodo è una Provincia e gli Archi rappresentano i confini condivisi.


* **Cruciale:** Identificare i "Coastal Nodes" (Land connessa a Ocean) per la logica navale.



### Step 1.3: Spatial Abstraction Layer

* **Task:** Creare `spatial_translator.py`.
* **Logica:**
* `describe_geography(nation_id)`: Restituisce stringhe come *"You are a continental power controlling 12 provinces..."*.
* `get_border_threats(nation_id)`: Analizza il grafo per dire *"You share a long border (5 provinces) with Hostile Nation B."*.



### Step 1.4: Deterministic Rules Oracle

* **Task:** Aggiornare `rules_engine.py`.
* **Logica:**
* **Topological Checks:** `can_move_troops(from, to)` (Pathfinding).
* **Resource Checks:** `can_afford(cost)`.
* **Diplomatic Hard-Locks:** `can_trade(target)` returns False if no Treaty exists.



### Step 1.5: The Genesis Module

* **Task:** Creare `genesis.py`.
* **Logica:**
* **Cold Start Fix:** Routine "Fast-Forward" pre-Turno 1.
* **Algorithmic History:** Assegna valori iniziali alla `trust_matrix` basandosi sulla distanza geografica (vicini = più frizione).
* **Narrative Backing (Optional):** Genera stringhe di "Storia Antica" per la memoria a lungo termine.



---

## 🧠 FASE 2: The Cognitive Agent Layer (The Brain)

**Obiettivo:** Implementare l'architettura **Hierarchical Cabinet** (Presidente + 4 Ministri).

### Step 2.1: Cabinet Structure

* **Task:** Creare `agent_cabinet.py`.
* **Struttura:**
* **Minister of Defense:** Analizza output spaziale. Goal: Sicurezza Territoriale.
* **Minister of Economy:** Usa `scipy`. Goal: Massimizzare PIL/Welfare.
* **Minister of Foreign Affairs:** Analizza `trust_matrix`. Goal: Alleanze.
* **Public Opinion (Autonomous):** Usa **Silicon Sampling**. Triggera eventi se `Satisfaction` è bassa.
* **The President (Aggregator):** Riceve proposte, risolve conflitti, output finale.



### Step 2.2: Hybrid Advisors Implementation

* **Task:** Creare `advisors.py`.
* **Economic Solver:** Implementare `scipy.optimize.linprog` per calcoli ottimali prima della generazione testo.
* **Opinion Sampler:** Iniettare dati demografici nel prompt.

### Step 2.3: Cabinet Workflow (Proposal -> Exec -> React)

* **Task:** Aggiornare `agent_core.py`.
* **Loop:**
1. **Proposal Phase:** I 3 Ministri generano proposte JSON strutturate.
2. **Executive Phase:** Il Presidente seleziona/modifica proposte -> `DiplomaticEnvelope`.
3. **Reaction Phase:** L'Opinione Pubblica valuta il nuovo stato -> Trigger Eventi (es. Strike).



---

## 🤝 FASE 3: Actions & Diplomacy

**Obiettivo:** Implementare lo specifico Action Space della Metodologia.

### Step 3.1: Diplomatic Envelope Protocol

* **Task:** Aggiornare `schemas.py`.
* **Struttura:**
```python
class DiplomaticEnvelope(BaseModel):
    sender_id: str
    target_id: str
    public_statement: str  # Retorica (può essere ingannevole)
    private_intent: Literal["Sincere", "Bluff", "Threat"]
    payload: ActionPayload   # Logica eseguibile

```



### Step 3.2: Strategic Action Space Implementation

* **Task:** Creare `actions_registry.py`.
* **Defense Actions:** `Mobilize_Unit`, `Fortify_Province`, `Deploy_Troops`, `Nuclear_Option`, `Covert_Espionage`.
* **Economic Actions:** `Invest_Welfare`, `Trade_Proposal`, `Impose_Sanctions`, `Raise_War_Tax`, `Develop_Tech`.
* **Diplomatic Actions:** `Send_Diplomatic_Message`, `Propose_Alliance`, `Formal_Declaration_of_War`, `Break_Treaty`, `Request_Peace`.
* **Public Opinion Events:** `General_Strike`, `Civil_Unrest`, `Rally_Effect`.

### Step 3.3: Action Executioner

* **Task:** Aggiornare `rules_engine.py`.
* **Logica:** Mappare ogni tipo di `payload` a una funzione di modifica dello stato.
* *Example:* `Invest_Welfare` -> Deduct Budget -> Increase Satisfaction Score.



---

## 🔍 FASE 4: Explainability & Counterfactuals

**Obiettivo:** Tracciabilità e Controfattuali (Layered CoT).

### Step 4.1: Structured Logging

* **Task:** Creare `xai_logger.py`.
* **Requisito:** Loggare l'intero "Cabinet Debate" (Proposte Ministri -> Decisione Presidente) per analizzare *perché* una decisione è stata presa.

### Step 4.2: Layered Prompting & Oracle

* **Task:** Creare `counterfactuals.py`.
* **Logic:**
* **Trace:** Log Perception -> Reasoning -> Justification.
* **Oracle:** Implementare `test_counterfactual(state, action)`: Clone state -> Try Action -> Return Rule Violation (e.g., "Cannot Trade: No Treaty").



---

## 📊 FASE 5: Simulation & Validation

**Obiettivo:** Validazione scientifica (RQs).

### Step 5.1: Main Loop

* **Task:** `main.py`.
* **Logica:** Init Genesis -> Loop Turni (Cabinet Proposal -> Pres Act -> World Update -> Opinion React).

### Step 5.2: Metrics & Evaluation

* **Task:** `evaluator.py`.
* **RQ1 (Adaptation):** Misurare correlazione Geografia (Isola) vs Tech (Marina).
* **RQ2 (Deception):** Misurare divergenza `Public Statement` vs `Payload`.
* **RQ3 (Stability):** Misurare evoluzione `Trust Matrix` e Clustering Alleanze.

---

## 🖥️ FASE 6: Scientific Dashboard (Web UI)

**Obiettivo:** Analisi visuale post-mortem e runtime.

### Step 6.1: Simulation Explorer (Streamlit)

* **Task:** `dashboard.py`.
* **Funzionalità:**
* **Simulation Registry:** Tabella per visualizzare tutte le simulazioni passate.
* **Map Replay:** Slider temporale per vedere l'evoluzione Voronoi.



### Step 6.2: Decision Inspector

* **Task:** `inspector_ui.py`.
* **Funzionalità:**
* **Cabinet Inspector:** Visualizza il dibattito interno di una nazione.
* **Logs Tab:** Visualizzazione JSON raw.



---

## 🤖 Prompt for Coding Assistant (Phase 1 Update)

**Copia e incolla questo prompt nella chat del tuo Coding Assistant:**

Agisci come Senior Python Engineer per un progetto di simulazione scientifica (GeoMAS).
Obiettivo: Implementare la Fase 1 (World Engine) e la Fase 1.5 (Genesis) seguendo rigorosamente le specifiche.

**Task 1: Schemi Dati (schemas.py)**
Usa Pydantic. Definisci modelli gerarchici per:

* `Province` (id, coordinates, terrain, resources, owner).
* `Nation` (id, ministerial_state: {budget, satisfaction, tech_tree}).
* `WorldState` (map_data, nations, turn, trust_matrix, treaties).
* `DiplomaticEnvelope` (public_text, private_intent, payload).

**Task 2: Map Engine (map_engine.py)**
Implementa la generazione Voronoi con:

* Lloyd's Relaxation.
* Generazione Continenti (Noise-based).
* Assegnazione Risorse e Capitali.
* Conversione in Grafo NetworkX (essenziale per il pathfinding).

**Task 3: Genesis Module (genesis.py)**
Implementa una funzione `initialize_history(world_state)` che:

* Popola la `trust_matrix` iniziale basandosi sulla distanza geografica (vicini = trust più basso).
* (Opzionale per ora) Placeholder per la generazione di storia testuale.

Usa Type Hints e docstrings. Il codice deve essere pronto per l'integrazione con Streamlit.