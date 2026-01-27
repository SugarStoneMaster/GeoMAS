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
- [ ] Aggiungere `ActionType.MOVE_TROOPS`
- [ ] Pathfinding via terra (grafo adiacenza)
- [ ] Movimento via mare (Navy transport)
- [ ] Costo energy per movimento
- [ ] Test MOVE_TROOPS

#### 4. Combat Resolution
- [ ] Definire formula combattimento
- [ ] Moltiplicatori terreno (MOUNTAIN difesa ×1.5)
- [ ] Perdite e conquista provincia
- [ ] Impatto Trust e Satisfaction
- [ ] Test Combat

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