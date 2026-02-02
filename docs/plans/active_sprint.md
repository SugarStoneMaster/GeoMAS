# 🚀 Sprint: Fase 7.6 - Persistence Layer & XAI Database

**Status:** In Progress
**Obiettivo:** Salvare stato simulazione per analisi post-hoc e explainability

---

## 🎯 Requisiti

### Funzionali
1. Salvare lo stato completo del mondo ad ogni turno
2. Salvare tutte le decisioni degli agenti (envelopes)
3. Salvare metriche comportamentali (deception, coherence)
4. Query temporali: "cosa è successo al turno X?"
5. Export per analisi esterna

### Non-Funzionali
1. **Determinismo**: A parità di seed, dati identici
2. **Performance**: Non rallentare la simulazione (~10ms/turno max)
3. **Semplicità**: No dipendenze server esterni
4. **Portabilità**: File-based, copiabile
5. **Analisi**: Supporto query analitiche

---

## ✅ Decisione: DuckDB

**Database scelto:** DuckDB (file-based OLAP)

**Motivazioni:**
- Ottimizzato per query analitiche (XAI, Jupyter)
- SQL standard
- Compressione ZSTD nativa
- Zero config (un file)
- Pandas/Polars integration

**Dimensioni stimate:**
- ~70 KB per turno (senza genesis events)
- 100 turni = ~7 MB (non compresso)
- Con compressione: ~2-3 MB

---

## 📊 Schema Finale

### File: `data/genesis_{seed}.duckdb` (separato)
```sql
-- Eventi storici generati dal Genesis module
CREATE TABLE genesis_events (
    year INT,
    event_type VARCHAR,
    nations JSON,
    description VARCHAR
);

-- Snapshot mondo post-genesis (turno 0)
CREATE TABLE initial_state (
    world_json JSON
);
```

### File: `data/simulation_{id}.duckdb`
```sql
-- Metadata simulazione
CREATE TABLE simulation (
    id UUID PRIMARY KEY,
    genesis_seed INT,
    simulation_seed INT,
    n_cells INT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_turns INT
);

-- Snapshot mondo per turno (provinces + nations + trust + relations)
CREATE TABLE snapshots (
    turn INT PRIMARY KEY,
    provinces_json JSON,
    nations_json JSON,
    trust_matrix JSON,
    relationship_matrix JSON
);

-- Decisioni agenti (CountryEnvelope)
CREATE TABLE envelopes (
    turn INT,
    nation_id VARCHAR,
    envelope_json JSON,
    PRIMARY KEY (turn, nation_id)
);

-- Metriche comportamentali (colonne flat per query veloci)
CREATE TABLE behaviors (
    turn INT,
    nation_id VARCHAR,
    deception_total FLOAT,
    deception_defense FLOAT,
    deception_economic FLOAT,
    deception_foreign FLOAT,
    coherence_score FLOAT,
    global_strategy VARCHAR,
    PRIMARY KEY (turn, nation_id)
);
```

---

## 📋 Task Breakdown

### 1. Package Setup ✅
- [x] Creare `geomas/db/__init__.py`
- [x] Installare `duckdb` dependency
- [x] Creare `geomas/db/connection.py` (SimulationDB class)

### 2. Serialization Helpers ✅
- [x] `serialize_world_snapshot()` (senza numpy issues)
- [x] `serialize_envelope()`
- [x] `convert_numpy()` per conversione ricorsiva
- [x] Gestione Enum → string

### 3. SimulationDB Class ✅
- [x] `initialize()` - crea tabelle + metadata
- [x] `save_snapshot()` - salva world state
- [x] `save_envelope()` - salva decisioni agenti
- [x] `save_behavior()` - salva metriche
- [x] `load_snapshot()` - carica world state
- [x] `load_envelopes()` - carica decisioni
- [x] `load_behaviors()` - carica metriche

### 4. Query Interface ✅
- [x] `get_behavior_timeline(nation_id) -> DataFrame`
- [x] `get_simulation_info() -> dict`
- [x] `export_behaviors_csv(path)`

### 5. Tests ✅
- [x] Test roundtrip serialization (14 test passati)
- [x] Test save/load simulation
- [x] Test query interface
- [x] Test context manager

---

## 🔜 Prossimi Step

### 6. Deserialization (JSON → Pydantic) ✅
- [x] `deserialize_provinces(json) -> Dict[int, ProvinceState]`
- [x] `deserialize_nations(json) -> Dict[str, NationState]`
- [x] `load_world_at_turn(turn) -> WorldState`

### 7. SimulationEngine Integration ✅
- [x] Aggiungere parametro `db_path: Optional[str]` a SimulationEngine
- [x] Hook in `step()` → auto-persist dopo ogni turno
- [x] Salvare snapshot iniziale (turno 0)
- [x] Save envelopes e behavior metrics per turno

### 8. In-Memory Cache
- [ ] Cache ultimi N turni per context LLM
- [ ] Evitare query DB durante simulazione

### 9. Genesis DB (Opzionale)
- [ ] Separare eventi storici in DB dedicato
- [ ] Riutilizzo genesis tra simulazioni

---

## 📌 Notes
- Genesis DB opzionale, può essere riusato tra simulazioni
- JSON per dati complessi, colonne flat per metriche
- In-memory cache per context LLM (ultimi 10-20 turni)
- File DB in `data/` directory
- Package rinominato da `persistence` a `db`