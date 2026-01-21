# 🗺️ GeoMAS Master Roadmap

> **Ultimo Aggiornamento:** Gennaio 2026

## 🌍 FASE 1: The World Engine (Spatial & Physics) ✅
**Obiettivo:** Creare un mondo deterministico procedurale.
- [x] 1.1 Modelli Pydantic (`schemas/world.py`, `schemas/protocol.py`, `schemas/actions.py`)
- [x] 1.2 Generazione Mappa Voronoi (`world/map_engine.py` - Lloyd's Relaxation)
- [x] 1.3 Grafo di Adiacenza NetworkX (`world/spatial_manager.py`)
- [x] 1.4 Deterministic Rules Oracle Base (`core/rules_engine.py`)
- [x] 1.5 Genesis Module (`core/genesis.py` - Config GA-optimized)

## 🧠 FASE 2: The Cognitive Layer (Agents) ✅
**Obiettivo:** Implementare il Governo Neuro-Simbolico.
- [x] 2.1 Schemi Cognitivi (`GlobalStrategy`, `CountryEnvelope`, `*Intent` enums)
- [x] 2.2 Struttura Agente Cabinet (`agents/nation_agent.py` + `agents/ministers.py`)
    - [x] Executive Override via `DecisionSource` enum
    - [x] Global Strategy fissa per run
- [x] 2.3 Integrazione LLM (`agents/llm_client.py` - Instructor/LiteLLM)
- [ ] 2.4 Public Opinion Logic ⚠️ **NON IMPLEMENTATO** (descritto in tesi ma assente)

## 🤝 FASE 3: Actions & Diplomacy ✅ (Parziale)
**Obiettivo:** Interazione tra agenti.
- [x] 3.1 Waterfall Logic nel Rules Engine (parziale - solo subset azioni)
- [ ] 3.2 Registro Azioni completo ⚠️ **PARZIALE**
    - [x] MOBILIZE_UNIT, FORTIFY_PROVINCE, INVEST_WELFARE, SEND_DIPLOMATIC_MESSAGE
    - [ ] DEPLOY_TROOPS, TRADE_PROPOSAL, NUCLEAR_OPTION, alleanze, guerre
- [x] 3.3 Deception Score (`analysis/deception.py`)

---

## 🔧 FASE 3.5: Actions Refactoring 🟡 **PLANNED**
**Obiettivo:** Riorganizzare il sistema azioni con Strategy Pattern.

> **Motivazione:** Attualmente le azioni sono un enum monolitico con payload generico (`Dict[str, Any]`). 
> Ogni nuova azione richiede modifiche a 3+ file. Il refactoring permette azioni self-contained.

### Struttura Proposta
```
geomas/schemas/actions/
├── __init__.py       # Re-export + backward compat
├── base.py           # BaseAction ABC, ActionResult
├── defense.py        # CreateUnit, MoveTroops, FortifyProvince, NuclearOption
├── economy.py        # InvestWelfare, TradeProposal, ImposeSanctions, etc.
├── foreign.py        # SendMessage, ProposeAlliance, DeclareWar, etc.
└── public_opinion.py # GeneralStrike, CivilUnrest, RallyEffect
```

### Checklist
- [ ] 3.5.1 Creare `actions/base.py` con `BaseAction` ABC e `ActionResult`
- [ ] 3.5.2 Creare `actions/defense.py` con azioni militari
- [ ] 3.5.3 Creare `actions/economy.py` con azioni economiche
- [ ] 3.5.4 Creare `actions/foreign.py` con azioni diplomatiche
- [ ] 3.5.5 Creare `actions/public_opinion.py` con eventi (trigger automatici)
- [ ] 3.5.6 Refactoring `rules_engine.py` per usare `action.execute()`
- [ ] 3.5.7 Verificare test esistenti (`test_rules_engine.py`, `test_schemas.py`)
- [ ] 3.5.8 Aggiungere unit test per ogni action class

> 📄 **Piano Dettagliato:** Vedi `implementation_plan.md` negli artifact.

---

## 🔍 FASE 4: Explainability (XAI) 🔴 **TODO**
**Obiettivo:** Tracciabilità e Controfattuali.
- [ ] 4.1 Structured Logger (Cabinet Debate)
- [ ] 4.2 Counterfactual Engine (Forking)
- [ ] 4.3 Query Interface ("Why did you do X?")

> **Nota:** Il modulo `xai/` esiste ma è vuoto.

## 📊 FASE 5: Simulation Loop & Validation ✅ (Base)
**Obiettivo:** Esecuzione scientifica.
- [x] 5.1 Main Loop Turn-based (`core/simulation.py`)
- [ ] 5.2 Metriche di Stabilità e Coerenza
- [ ] 5.3 Batch Running (Multi-seed)

## 🖥️ FASE 6: Dashboard & Analysis ✅
**Obiettivo:** Visualizzazione.
- [x] 6.1 Streamlit Dashboard (`web/app.py`)
- [x] 6.2 Map Explorer (Voronoi rendering con Matplotlib)
- [x] 6.3 Trust Matrix Viewer
- [ ] 6.4 Decision Inspector Log (parziale)

---

## 📋 Gap Critici Identificati

| Gap | Impatto | Priorità |
|-----|---------|----------|
| Public Opinion Agent mancante | Nessun feedback loop interno | Alta |
| XAI Layer vuoto | Nessuna explainability | **Critica** (Fase 4) |
| Azioni incomplete in Rules Engine | Simulazione limitata | Media |
| Deep Genesis (LLM) assente | Solo storia algoritmica | Bassa |