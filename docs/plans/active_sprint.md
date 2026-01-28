# 🏃 Active Sprint: Phase 4 (Advanced Military System)

**Obiettivo:** Implementare unità militari, movimento e combattimento.

---

## ✅ Completed (Phase 3.6 - UI Refactoring)
- [x] Refactoring `web/app.py` in moduli (components/, views/)
- [x] Layout 3-colonne (Stats | Map | Intel)
- [x] Controlli spostati in alto (no sidebar)
- [x] Trust Matrix sotto la mappa
- [x] Visualizzazione acque territoriali
- [x] Highlight nazione selezionata
- [x] 71 test passati

---

## 📝 Sprint Backlog: Military System

### 🎯 Sprint Goal
Implementare il sistema militare base: creazione unità, movimento truppe, e combattimento.

---

### Task Breakdown

#### 1. Unit Types & Constraints
- [x] Creare `UnitType` Enum in `schemas/world.py`
- [x] Definire costi unitari (budget, materials, energy, pop)
- [x] Vincoli posizionamento per terreno

#### 2. CREATE_UNIT Action
- [x] Aggiungere `ActionType.CREATE_UNIT`
- [x] Implementare validazione (budget, materials, pop)
- [x] Handler che deduce risorse e crea unità
- [x] Test CREATE_UNIT

#### 3. MOVE_TROOPS Action
- [x] Aggiungere `ActionType.MOVE_TROOPS`
- [x] Pathfinding via terra (grafo adiacenza)
- [x] Movimento via mare (Navy transport)
- [x] Costo energy per movimento
- [x] Test MOVE_TROOPS

#### 4. Combat Resolution
- [x] Definire formula combattimento
- [x] Moltiplicatori terreno (MOUNTAIN difesa ×1.5)
- [x] Perdite e conquista provincia
- [x] Impatto Trust e Satisfaction
- [x] **Naval Landing (sbarco anfibio unificato):**
  1. Nave entra in cella acqua territoriale nemica
  2. Se ci sono navi nemiche → duello nave vs navi
     - Vince → distrugge navi + sbarca soldati in costa adiacente random
  3. Se NO navi ma ci sono unità su costa adiacente → duello nave vs difensori
     - Vince → sbarca soldati su quella costa
  4. Se NO navi e NO unità → sbarco automatico su costa adiacente random
  5. In tutti i casi: nave distrutta, soldati = population della nave
- [x] Test Combat

#### 5. NUCLEAR_OPTION (Base)
- [ ] Validazione (possiede nukes)
- [ ] Effetti devastanti
- [ ] Reazione diplomatica globale
- [ ] Test Nuclear

---

## 📌 Note

> **Focus:** Iniziare da CREATE_UNIT e MOVE_TROOPS, che sono prerequisiti per tutto il resto.

---

## 🚧 Dependencies
- Trust Matrix (già implementata)
- Territorial Waters (già implementata)
- Power Projection (già implementata)