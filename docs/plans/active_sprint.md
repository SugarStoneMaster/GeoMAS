# 🏃 Active Sprint: Phase 3.5 (Refactoring)

**Obiettivo:** Migliorare modularità, leggibilità e manutenibilità del codebase.

---

## ✅ Completed (Phase 3)
- [x] Schema Updates (ProvinceState, NationState, UnitType)
- [x] World Engine Updates (Territorial Waters, Nukes, Production)
- [x] Resource Consumption Logic (`economy.py`)
- [x] Trade Oracle (`trade_oracle.py`)
- [x] Action System Updates (INVEST_WELFARE, RAISE_WAR_TAX, TRADE_PROPOSAL)
- [x] Tests (66 test passati)

---

## 📝 Sprint Backlog: Refactoring

### 🎯 Sprint Goal
Rendere il codebase più modulare, pulito e manutenibile prima di procedere con Phase 4.

---

### Aree di Refactoring

#### 1. Rimozione Codice Legacy ✅
- [x] Rimosso `ResourceBundle` (sostituito da `*_production` fields)
- [x] Rimosso `MinisterialState.budget` (sostituito da `NationState.total_budget`)
- [x] Aggiornato `map_engine.py`, `genesis.py`, `spatial_translator.py`
- [x] Aggiornato `ministers.py`, `web/app.py`, `rules_engine.py`
- [x] Aggiornati tutti i test

#### 2. Riorganizzazione Moduli
- [ ] Valutare struttura package
- [ ] Separare responsabilità dove necessario

#### 3. Pulizia Schemi
- [ ] Consolidare field duplicati
- [ ] Rimuovere campi `resources` legacy se non più usati

#### 4. Documentazione
- [ ] Docstrings per funzioni pubbliche
- [ ] Commenti esplicativi dove necessario

#### 5. Test Updates
- [ ] Allineare test ai refactoring effettuati

---

## 📌 Note

> **Approccio incrementale:** Il refactoring sarà gestito man mano durante lo sviluppo, senza un piano rigido predefinito.

---

## 🚧 Next Phase
- Phase 4: Advanced Military System