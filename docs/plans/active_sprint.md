# 🚀 Sprint Corrente: Synchronization, Memory & Persistence

**Status:** Planning | **Priority:** High

---

## 🎯 Obiettivo
Sincronizzare l'esecuzione fisica (`ActionEngine`) con la memoria cognitiva (`ContextManager`) e garantire la persistenza totale dello stato per abilitare XAI e rigenerazione della simulazione.

---

## 📋 Tasks

### 1. Action-Outcome Synchronization
- [x] **Payload Update:** Aggiunta `execution_outcome` a tutti gli schema di azione.
- [x] **Handler Update:** Modificati gli handler per popolare l'outcome.
- [x] **Context Integration:** Aggiornato `ContextManager` per usare outcome reali.

### 2. Context Manager & Memory Refinement
- [x] **Ego-Centric Memory:** Distinzione tra eventi globali e azioni private.
- [x] **Trust Trend Logic:** Ottimizzato il calcolo e la persistenza dei trend.

### 3. Full State Persistence (Explainability Base)
- [x] **DB Schema Extension:** Salvataggio stato `ContextManager` (memory_json).
- [x] **Simulation Forking Base:** Implementato `SimulationEngine.load_state(turn)` per ricostruzione totale dell'universo (mondo + memoria).
- [x] **Token Observability:** Integrata tabella `token_usage` e calcolo costi automatico per turno.
- [x] **Prompt Persistence:** Cattura e salvataggio di `system_prompt` e `input_prompt` per ogni decisione presidenziale nell'envelope (visibili in DB per analisi XAI).
- [x] **Regression Testing:** Ripristinato test di integrazione (`tests/integration/test_regeneration.py`) con mock LLM per garantire la stabilità del ripristino stato.

---

## 📌 Design Notes

**Sincronizzazione Verità:**
L'`ActionEngine` è l'unica fonte di verità. Il `ContextManager` deve diventare un consumatore passivo di outcome validati, eliminando la duplicazione della logica di validazione nel parser di eventi.

**Explainability:**
Ogni decisione dell'agente deve essere tracciabile non solo tramite il prompt, ma anche tramite la storia di successi/fallimenti che l'agente ha percepito nei turni precedenti.