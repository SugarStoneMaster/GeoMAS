# 🏃 Active Sprint: Phase 3 (Resource & Economic Model)

**Obiettivo:** Implementare il sistema economico completo con risorse, popolazione e Trade Oracle.

---

## ✅ Completed (Phase 1 & 2)
- [x] World Engine & Genesis
- [x] Agent Architecture (LLM + Ministers)
- [x] Basic Simulation Loop & UI

---

## 📝 Sprint Backlog

### 🎯 Sprint Goal
Creare le fondamenta economiche su cui costruire militare e diplomazia.
**Criterio di successo:** Una nazione può produrre risorse, consumarle, e accettare/rifiutare trade in modo deterministico.

---

### 1. Schema Updates (`geomas/schemas/`) ✅

#### 1.1 Estendere `ProvinceState` in `world.py` ✅
```python
# Aggiunto:
food_production: float = 0.0
energy_production: float = 0.0
materials_production: float = 0.0
tax_revenue: float = 0.0
workers: int = 0
soldiers: int = 0
aircraft: int = 0
navy: int = 0
```

#### 1.2 Estendere `NationState` in `world.py` ✅
```python
# Aggiunto:
total_food: float = 0.0
total_energy: float = 0.0
total_materials: float = 0.0
total_budget: float = 0.0
power_projection: float = 0.0
nukes: int = 0
territorial_water_ids: List[int] = []
```

#### 1.3 Creare `UnitType` Enum in `actions.py` ✅
```python
class UnitType(str, Enum):
    SOLDIER = "SOLDIER"
    NAVY = "NAVY"
    AIRCRAFT = "AIRCRAFT"
```

---

### 2. World Engine Updates (`geomas/world/`) ✅

#### 2.1 Territorial Waters Logic in `map_engine.py` ✅
- [x] Province OCEAN adiacenti a una sola nazione → owned (acque territoriali)
- [x] Popolare `territorial_water_ids` in `NationState`

#### 2.2 Nukes Distribution in `map_engine.py` ✅
- [x] 2-3 nazioni random (seed-based) ricevono 1-5 nukes
- [x] Le altre nazioni: 0 nukes

#### 2.3 Resource Production + Initial Army ✅
- [x] Population random per terreno (COASTAL +50%, MOUNTAIN -50%)
- [x] Workers = population - soldiers (2-8% inizia come soldati)
- [x] Production basata su terreno e workers
- [x] Tax revenue = population * 0.1
- [x] Initial budget 500-3000 random per nazione
- [x] Power projection calcolata

---

### 3. Resource Consumption Logic (`geomas/core/`) ✅

#### 3.1 Creare `economy.py` ✅
Funzioni pure implementate:
- [x] `calculate_food_consumption()` - 1 food/persona
- [x] `calculate_energy_consumption()` - 0.5 energy/persona
- [x] `calculate_materials_consumption()` - mantenimento militare
- [x] `calculate_production_penalty()` - penalità workforce
- [x] `calculate_tax_collection()` - somma tax province
- [x] `calculate_nation_aggregates()` - aggregati nazione
- [x] `calculate_power_projection()` - formula pesata
- [x] `calculate_starvation_casualties()` - fame
- [x] `calculate_energy_penalty()` - blackout

#### 3.2 Aggiornare `simulation.py` ✅
- [x] Economy Phase a inizio turno
- [x] Raccolta tasse, produzione, consumo
- [x] Se food < 0: perdita popolazione (starvation)
- [x] Se energy < 0: penalità produzione

---

### 4. Trade Oracle (`geomas/core/trade_oracle.py`) ✅

#### 4.1 Implementare la Formula ✅
```python
def calculate_trade_score(offer: TradeOffer, world: WorldState) -> Tuple[float, str]
    # TradeScore = (E_val × M_scarcity) - (R_risk × P_projection)
    # Trade accettato se TradeScore > 0
```

#### 4.2 Componenti ✅
- [x] `E_val`: Base prices (Food=1, Energy=2, Materials=3)
- [x] `M_scarcity`: 1.0-5.0 basato su turni di scorta rimanenti
- [x] `R_risk`: `(50 - trust) / 10` se trust < 50, else 0
- [x] `P_projection`: Alto per Materials/Energy se receiver è forte

#### 4.3 Creare `TradeOffer` Schema ✅
```python
class TradeOffer(BaseModel):
    sender_id: str
    receiver_id: str
    give: Dict[str, float]
    receive: Dict[str, float]
    duration_turns: int = 1
```

---

### 5. Action System Updates (`geomas/core/rules_engine.py`) ✅

#### 5.1 INVEST_WELFARE ✅
- [x] Costo: Budget (amount parametro)
- [x] Effetto: `satisfaction += log(amount) * 0.02` (diminishing returns)
- [x] Check: Budget sufficiente

#### 5.2 RAISE_WAR_TAX ✅
- [x] Prerequisito: `satisfaction >= 0.20`
- [x] Effetto: `budget += population * 0.1`, `satisfaction -= 0.15`
- [x] Non eseguibile sotto soglia

#### 5.3 TRADE_PROPOSAL ✅
- [x] Usa Trade Oracle per accettazione automatica
- [x] Se accettato: trasferisci risorse
- [x] Aumenta Trust tra le due nazioni (+0.02)

---

### 6. Tests (`tests/core/`) ✅

#### 6.1 `test_economy.py` ✅ (16 tests)
- [x] Test consumo (food, energy, materials)
- [x] Test production penalty workforce
- [x] Test tax collection
- [x] Test aggregates
- [x] Test power projection
- [x] Test starvation/energy penalty

#### 6.2 `test_trade_oracle.py` ✅ (21 tests)
- [x] Test scarcity multiplier
- [x] Test relational risk
- [x] Test power projection impact
- [x] Test trade score calculation
- [x] Test trade acceptance/rejection

---

## 📌 Note Importanti

1. **Determinismo:** Tutte le nuove funzioni devono usare `rng` passato come argomento
2. **Pydantic:** Ogni nuovo schema deve essere un `BaseModel`
3. **Backward Compatibility:** I test esistenti devono continuare a passare, eventualmente vanno aggiornati in base alle nuove modifiche
4. **Tech Level:** Rimosso dalla scope (da riprendere in futuro)
5. **Casus Belli:** Rimandato a fase successiva

---

## 🚧 Out of Scope (Fasi Successive)
- CREATE_UNIT (Fase 4 - Military)
- MOVE_TROOPS (Fase 4 - Military)
- Combat Resolution (Fase 4 - Military)
- NUCLEAR_OPTION (Fase 4 - Military)
- Diplomacy Actions (Fase 5)
- Public Opinion Triggers (Fase 6)