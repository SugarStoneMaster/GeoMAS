# 🏃 Active Sprint: Phase 1 (World Engine & Physics)

**Obiettivo:** Completare il motore fisico deterministico e le regole di validazione.

## ✅ Completed
- [x] **Data Structures:** Definiti `ProvinceState`, `NationState`, `WorldState` in `geomas/schemas/models.py`.
- [x] **Map Generation:** Implementato Voronoi + Continenti + Pydantic Mapping in `geomas/world/map_engine.py`.
- [x] **Visualization:** Creata Dashboard Streamlit funzionante in `geomas/ui/app.py`.
- [x] **Spatial Graph:** Implementato `SpatialManager` in `geomas/world/spatial_manager.py`.
- [x] **Rules Oracle:** Implementato `ActionValidator` in `geomas/core/rules_engine.py`.
- [x] **Spatial Abstraction:** Implementato `SpatialTranslator` in `geomas/world/spatial_translator.py`.

## 📝 To-Do List (Final Step)

### 1. Genesis Module (`geomas/core/genesis.py`)
*Dalla Roadmap 1.5 - Algorithmic History*
- [ ] Implementare `initialize_history(world: WorldState, years: int = 50)`.
- [ ] **Algoritmo Fast-Forward:** Simulare N turni semplificati senza LLM.
    - [ ] **Adjacency Friction:** Ridurre Trust tra vicini (conflitti di confine).
    - [ ] **Resource Scarcity:** Aumentare Trust se c'è complementarità di risorse (es. Cibo vs Energia).
- [ ] Popolare la `Trust Matrix` finale basata su questi eventi.
- [ ] Generare un log sintetico degli eventi storici ("Year 10: Border skirmish between Agria and Krell").

---
**Nota:** Al termine di questo task, la Fase 1 è ufficialmente conclusa.