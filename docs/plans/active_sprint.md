# 🚀 Sprint Corrente: Synchronization, Memory & Persistence

**Status:** Planning | **Priority:** High

---

## 🎯 Obiettivo
Sincronizzare l'esecuzione fisica (`ActionEngine`) con la memoria cognitiva (`ContextManager`) e garantire la persistenza totale dello stato per abilitare XAI e rigenerazione della simulazione.

---

## 📋 Tasks

### 1. Action-Outcome Synchronization
- [ ] **Payload Update:** Aggiungere `ExecutionOutcome` (status, reason, details) a tutti gli schema di azione (`DefenseActionItem`, `EconomicPayload`, `ForeignPayload`).
- [ ] **Handler Update:** Modificare gli handler in `actions/` affinché scrivano il risultato dell'esecuzione direttamente nel payload dell'envelope.
- [ ] **Context Integration:** Aggiornare `ContextManager` per generare eventi e record d'azione basandosi sugli outcome reali invece che sulle pure intenzioni.

### 2. Context Manager & Memory Refinement
- [ ] **Ego-Centric Memory:** Rafforzare la distinzione tra `GlobalEvents` (pubblici) e `NationActions` (audit privato con dettagli tecnici di successo/fallimento).
- [ ] **Trust Trend Logic:** Ottimizzare il calcolo dei trend di trust basato sulla storia persistente.

### 3. Full State Persistence (Explainability Base)
- [ ] **DB Schema Extension:** Estendere `SimulationDB` per salvare lo stato interno del `ContextManager` (RelationshipSummaries, GlobalEvents, NationActions).
- [ ] **Simulation Forking Base:** Implementare `SimulationEngine.load_state(turn)` che ricostruisce non solo il mondo, ma anche la memoria degli agenti per riprendere la simulazione in modo coerente.
- [ ] **Token Observability:** Integrare i dati di consumo token nel record persistente del turno.

---

## 📌 Design Notes

**Sincronizzazione Verità:**
L'`ActionEngine` è l'unica fonte di verità. Il `ContextManager` deve diventare un consumatore passivo di outcome validati, eliminando la duplicazione della logica di validazione nel parser di eventi.

**Explainability:**
Ogni decisione dell'agente deve essere tracciabile non solo tramite il prompt, ma anche tramite la storia di successi/fallimenti che l'agente ha percepito nei turni precedenti.