# 🗺️ GeoMAS Master Roadmap

## 🌍 FASE 1: The World Engine (Spatial & Physics)
**Obiettivo:** Creare un mondo deterministico procedurale.
- [x] 1.1 Modelli Pydantic (`schemas.py`)
- [x] 1.2 Generazione Mappa Voronoi (`map_engine.py`)
- [x] 1.3 Grafo di Adiacenza NetworkX
- [x] 1.4 Deterministic Rules Oracle (Base)
- [ ] 1.5 Genesis Module (Init History)

## 🧠 FASE 2: The Cognitive Layer (Agents)
**Obiettivo:** Implementare il Governo Neuro-Simbolico.
- [ ] 2.1 Definizione Schemi Cognitivi (`GlobalStrategy`, `DiplomaticEnvelope`, `IntentEnums`).
- [ ] 2.2 Struttura Agente (Presidente + Ministri).
    - [ ] Implementare logica **Executive Override** (Source Tracking).
    - [ ] Implementare **Global Strategy Fissa** per run.
- [ ] 2.3 Integrazione LLM (Azure OpenAI con Instructor).
- [ ] 2.4 Public Opinion Logic.

## 🤝 FASE 3: Actions & Diplomacy
**Obiettivo:** Interazione tra agenti.
- [ ] 3.1 Implementazione Waterfall Logic nel Rules Engine.
- [ ] 3.2 Registro Azioni (War, Trade, Alliance).
- [ ] 3.3 Calcolo Deception Score (Public vs Private Intent).

## 🔍 FASE 4: Explainability (XAI)
**Obiettivo:** Tracciabilità e Controfattuali.
- [ ] 4.1 Structured Logger (Cabinet Debate).
- [ ] 4.2 Counterfactual Engine (Forking).
- [ ] 4.3 Query Interface ("Why did you do X?").

## 📊 FASE 5: Simulation Loop & Validation
**Obiettivo:** Esecuzione scientifica.
- [ ] 5.1 Main Loop (Turn-based).
- [ ] 5.2 Metriche di Stabilità e Coerenza.
- [ ] 5.3 Batch Running (Multi-seed).

## 🖥️ FASE 6: Dashboard & Analysis
**Obiettivo:** Visualizzazione.
- [ ] 6.1 Streamlit Dashboard.
- [ ] 6.2 Map Explorer.
- [ ] 6.3 Decision Inspector Log.