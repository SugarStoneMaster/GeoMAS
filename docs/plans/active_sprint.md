# 🚀 Sprint Corrente: Visual Testing & UI Integration

**Status:** Planning | **Priority:** High

---

## 🎯 Obiettivo
Passare dal testing headless al **Testing Visuale** integrato nella UI esistente.
Rimuovere tutti i mock/placeholders e abilitare le chiamate LLM reali per validare il comportamento degli agenti turno per turno.

---

## 📋 Tasks

### 1. UI Integration (Real LLM)
- [x] **Rimuovere Mock:** Sostituire i dati finti nella UI con dati reali dal `SimulationEngine`.
- [x] **Manual Turn Control:** 
    - [x] Disabilitare auto-play se presente.
    - [x] Il bottone "Next Turn" deve eseguire un singolo step (`engine.step()`) e attendere.
    - [x] Aggiornare lo stato della UI solo dopo il completamento del turno.

### 2. Inspector View (Prompts & Context)
- [x] **Agent Inspector Panel:**
    - [x] Quando si seleziona una nazione, mostrare tab per ogni agente (Presidente, Esteri, Economia, Difesa, Opinione).
    - [x] Per ogni agente mostrare:
        - **System Prompt:** Il prompt statico/dinamico usato.
        - **User/Input Prompt:** Il contesto fornito per quel turno.
        - **Output Raw:** La risposta JSON dell'LLM.

### 3. Event Log & History
- [x] **Event Viewer:**
    - [x] Sezione dedicata per consultare `ContextManager.global_events`.
    - [x] Filtri per turno e nazione.
    - [x] Visualizzazione chiara di come gli eventi vengono iniettati nel contesto (es. "Eventi Recenti").

---

## 📌 Design Notes

**Data Source:**
- L'UI deve leggere direttamente da `engine.agents` e `engine.world`.
- Per i prompt, useremo la struttura `last_trace` implementata in `NationAgent` e `Minister` (già pronta).

**UX Flow:**
1. Setup Simulazione (Nazioni, Map Seed) -> Start.
2. Dashboard visualizza Turno 0.
3. User clicca "Next Turn".
4. Spinner di caricamento (LLM in corso).
5. Dashboard si aggiorna al Turno 1.
6. User clicca su una Nazione -> Inspector apre i dettagli del ragionamento.