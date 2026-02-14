# 🚀 Sprint Corrente: Dashboard Visibility & Public Opinion Audit

**Status:** In Progress | **Priority:** High

---

## 🎯 Obiettivo
Migliorare la visibilità della simulazione rendendo tutti gli agenti (inclusa la Pubblica Opinione) osservabili nella dashboard e correggere il bug dei logs mancanti per l'agente opinione.

---

## 📋 Tasks

### 1. Dashboard Enhancements (Observability)
- [ ] **Public Opinion View:** Aggiungere una sezione dedicata nella dashboard per visualizzare System Prompt, Input Prompt e Structured Output della Pubblica Opinione (parità con Ministri/Presidente).
- [ ] **Unified Agent Inspection:** Assicurarsi che ogni turno mostri i dettagli di tutti gli attori coinvolti per facilitare il debug XAI.

### 2. Public Opinion Debug & Logging
- [ ] **Missing Logs Investigation:** Indagare perché, nonostante la chiamata avvenga, non ci sia traccia dei log/output della Pubblica Opinione nel ciclo di simulazione o nel DB in alcune condizioni.
- [ ] **Persistence Verification:** Verificare che i campi `raw_opinion_response` e le metriche di opinione siano correttamente salvati ad ogni turno.

---

## 📌 Design Notes

**Trasparenza Totale:**
La dashboard deve servire come "finestra" completa sul pensiero del MAS. Se un agente è attivo, il suo input/output deve essere ispezionabile immediatamente.

**Debug Deterministico:**
Usare i dati salvati nel DB per riprodurre i turni in cui l'opinione sembra "silenziosa" e verificare se si tratta di un errore di logica di esecuzione o solo di un problema di visualizzazione/persistenza.