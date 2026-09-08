# 🚀 Sprint Corrente: Counterfactual Analysis (XAI)

**Status:** Planned | **Priority:** Critical

---

## 🎯 Obiettivo
Implementare un sistema di **Controfattuali (Counterfactual Analysis)** ispirato al "Save Scumming". L'obiettivo è permettere all'utente di esplorare il "Perché" delle decisioni degli agenti forkando la simulazione da un punto specifico, forzando cambiamenti (azioni o stato) e osservando le differenze nel futuro immediato (Delta).

---

## ✅ Completato (Pre-requisiti)
- [x] Refactoring completo dei Prompt (Input/System) per tutti gli agenti.
- [x] Sistema di logging decisionale nel `ContextManager`.
- [x] Infrastruttura di salvataggio/caricamento stato (Database/Pickle).

---

## 📋 Tasks (Nuovi)

### 1. 🖥️ XAI Dashboard Interface (Streamlit)
*   **Integrated Analysis Mode**:
    *   **Mode Toggle**: Aggiungere switch nella Sidebar: `Live Simulation` vs `Post-Mortem / Forking`.
    *   **Turn Loader**: Il "Turn Slider" deve caricare lo stato reale dal DB, permettendo di visualizzare la mappa/dati di quel passato.
*   **Injection Controls (Sidebar)**:
    *   Visibile solo in `Analysis Mode`.
    *   **Target**: Selettore Nazione -> Ministro.
    *   **Constraint**: Dropdown "Forbid Action" / "Force Action".
    *   **Fork Run**: Bottone "Simulate Alternative Future (5 Turns)".
*   **Delta Visualization**:
    *   Comparare i risultati del fork con la timeline originale (se esiste per quei turni futuri).

### 2. 🎮 Simulation Engine: Forking & Injection
*   **Load & Fork**:
    *   Implementare/Verificare caricamento pulito dello stato (`WorldState`) da file/DB senza corrompere la run principale.
    *   Creare una `SimulationSession` separata per il fork.
*   **Prompt Injection Mechanism**:
    *   Modificare `NationAgent` e i `Ministers` per accettare un `injection_instruction` (es. "SYSTEM: You MUST NOT attack this turn").
    *   Questo vincolo deve essere inserito nel System Prompt o come User Message ad alta priorità.

### 3. 📊 Delta Analysis
*   **Data Capture**:
    *   Registrare metriche chiave (Trust, Risorse, Territorio) per N turni dopo il fork.
*   **Explanation Generation**:
    *   Generare un testo semplice (template-based o LLM) che spieghi la differenza: *"Nella run originale X ha attaccato e guadagnato Y. Nel fork (Wait), X è sopravvissuto ma ha perso Z."*

---

### 🚫 De-scoped
-   Analisi automatica su tutti i turni (troppo costoso).
-   Modifica complessa della topologia della mappa durante il fork.
-   Multi-turn counterfactuals profondi (limitarsi a 1-5 turni di horizon).