# 🚀 Sprint Corrente: Simulation Stability & Logic Refinement

**Status:** Planned | **Priority:** Critical

---

## 🎯 Obiettivo
Risolvere le criticità emerse dall'analisi dei log (Turn 1-15) per garantire una simulazione stabile, priva di errori di runtime e con agenti coerenti nelle loro decisioni spaziali e diplomatiche.

---

## ✅ Completato (Dashboard Visibility)
- [x] Aggiunta sezione Public Opinion nella dashboard.
- [x] Implementata visualizzazione dei prompt (system/input/output).
- [x] Risolto bug dei log mancanti per l'agente opinione.
- [x] Aggiunta pulsantiera "Run N Turns" per controllo granulare.

---

## 📋 Tasks (Nuovi)

### 🛡️ Defense Context Overhaul (High Priority)
1.  [ ] **Reachable Province Filter:**
    -   Instead of showing all neighbors, calculating valid moves in Python (Distance <= Range, Terrain Valid).
    -   The prompt will *only* list valid `target_province_id`s. This solves "VOID" and "Distance" errors at the source.
2.  [ ] **Simplified Layout:**
    -   Implement the user-provided "Turn 15" format.
    -   Sections: Military Overview, Force Deployment (Grouped), Threat Assessment, Attack Options, Recruitment Advice.
3.  [ ] **Logistics Section:** Explicitly list `→ Unit reaches: [A, B, C]` for every province with troops.

### 📉 Other Optimizations
1.  [ ] **Trade Clamping Feedback:** Implement explicit feedback when trades are clamped.
2.  [ ] **Trade Limits:** Clarify market capacity in Economy context.

### 🚫 De-scoped / Ignored
-   Fix VOID Terrain (Code-level) -> Solved by Context Filtering.
-   Streamlit Warnings -> Ignore.
-   Diplomatic Schizophrenia -> Ignore.