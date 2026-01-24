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

### 1. Schema Updates (`geomas/schemas/`)

#### 1.1 Estendere `ProvinceState` in `world.py`
```python
# Aggiungere:
food_production: float = 0.0
energy_production: float = 0.0
materials_production: float = 0.0
tax_revenue: float = 0.0
workers: int = 0  # Popolazione attiva (non militare)
soldiers: int = 0
aircraft: int = 0
navy: int = 0
```

#### 1.2 Estendere `NationState` in `world.py`
```python
# Aggiungere:
total_food: float = 0.0
total_energy: float = 0.0
total_materials: float = 0.0
nukes: int = 0  # Nazionale, non per provincia
territorial_water_ids: List[int] = []  # Province OCEAN possedute
```

#### 1.3 Creare `UnitType` Enum in `actions.py`
```python
class UnitType(str, Enum):
    SOLDIER = "SOLDIER"
    NAVY = "NAVY"
    AIRCRAFT = "AIRCRAFT"
```

---

### 2. World Engine Updates (`geomas/world/`)

#### 2.1 Territorial Waters Logic in `map_engine.py`
- [ ] Dopo assegnazione nazioni, scansionare province COASTAL
- [ ] Per ogni COASTAL, trovare OCEAN adiacenti
- [ ] Assegnare ownership OCEAN alla nazione (acque territoriali)
- [ ] Popolare `territorial_water_ids` in `NationState`

#### 2.2 Nukes Distribution in `map_engine.py`
- [ ] Selezionare 2-3 nazioni random (seed-based)
- [ ] Assegnare 1-5 nukes random a ciascuna
- [ ] Le altre nazioni: 0 nukes

#### 2.3 Resource Production Setup
- [ ] Al momento della creazione province, assegnare:
  - `food_production` basato su terreno (LAND alto, MOUNTAIN basso)
  - `energy_production` random (alcune province ricche)
  - `materials_production` random
  - `tax_revenue = population * tax_rate`
  - `workers = population` (inizialmente tutti lavoratori)

---

### 3. Resource Consumption Logic (`geomas/core/`)

#### 3.1 Creare `economy.py` (nuovo file)
Funzioni pure per calcoli economici:

```python
def calculate_food_consumption(total_population: int) -> float:
    """1 persona = 1 food/turno"""
    
def calculate_energy_consumption(total_population: int) -> float:
    """1 persona = 0.5 energy/turno"""
    
def calculate_materials_consumption(total_soldiers: int, total_navy: int, total_aircraft: int) -> float:
    """Mantenimento esercito"""
    
def calculate_production_penalty(workers: int, max_workers: int) -> float:
    """Meno lavoratori = meno produzione"""
```

#### 3.2 Aggiornare `simulation.py`
- [ ] A inizio turno: calcolare produzione/consumo per ogni nazione
- [ ] Aggiornare `total_food`, `total_energy`, etc.
- [ ] Se food < 0: perdita popolazione
- [ ] Se energy < 0: penalità produzione

---

### 4. Trade Oracle (`geomas/core/trade_oracle.py`)

#### 4.1 Implementare la Formula
```python
def calculate_trade_score(
    offer: TradeOffer,
    receiver_nation: NationState,
    sender_nation: NationState,
    trust: float
) -> float:
    """
    TradeScore = (E_val × M_scarcity) - (R_risk × P_projection)
    Trade accettato se TradeScore > 0
    """
```

#### 4.2 Componenti
- [ ] `E_val`: Base prices (Food=1, Energy=2, Materials=3)
- [ ] `M_scarcity`: 1.0 se stock OK, 2.0 se <50%, 5.0 se 0
- [ ] `R_risk`: `(50 - trust) / 10` se trust < 50, else 0
- [ ] `P_projection`: Alto per Materials/Energy se receiver è forte

#### 4.3 Creare `TradeOffer` Schema
```python
class TradeOffer(BaseModel):
    sender_id: str
    receiver_id: str
    give: Dict[str, float]  # {"food": 100, "energy": 50}
    receive: Dict[str, float]
    duration_turns: int = 1  # 1 = one-off, >1 = subscription
```

---

### 5. Action System Updates (`geomas/core/rules_engine.py`)

#### 5.1 INVEST_WELFARE
- [ ] Costo: Budget + Food
- [ ] Effetto: `satisfaction += log(amount) * 0.1` (diminishing returns)
- [ ] Check: Budget e Food sufficienti

#### 5.2 RAISE_WAR_TAX
- [ ] Prerequisito: `satisfaction >= 0.20`
- [ ] Effetto: `budget += tax_boost`, `satisfaction -= 0.15`
- [ ] Non eseguibile sotto soglia

#### 5.3 TRADE_PROPOSAL
- [ ] Usa Trade Oracle per accettazione automatica
- [ ] Se accettato: trasferisci risorse
- [ ] Costo trasporto: Budget se nazioni non confinanti
- [ ] Aumenta Trust tra le due nazioni

---

### 6. Tests (`tests/core/`)

#### 6.1 `test_economy.py` (nuovo)
- [ ] Test produzione risorse
- [ ] Test consumo popolazione
- [ ] Test penalità workforce

#### 6.2 `test_trade_oracle.py` (nuovo)
- [ ] Test E_val calculation
- [ ] Test M_scarcity multiplier
- [ ] Test R_risk factor
- [ ] Test P_projection impact
- [ ] Test trade acceptance/rejection

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