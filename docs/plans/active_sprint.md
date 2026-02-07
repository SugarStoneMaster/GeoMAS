# 🚀 Sprint Corrente: System Prompt Refinement

**Status:** In Progress | **Test:** 290 passati

---

## ✅ Fase 7.6 - Persistence & Context (COMPLETATA)

Tutti i componenti implementati e testati:
- SimulationDB, TurnCache, GenesisDB
- SpatialTranslator, MilitaryTranslator, NationProfileGenerator
- Prompt Architecture (5 system + 5 input builders)
- ContextManager con memory management
- TokenCounter con budget validation
- SimulationEngine e Agent integration

---

## 🔄 In Progress

### System Prompt Fixes
- [ ] Defense: aggiungere `unit_type` a MOVE_TROOPS
- [ ] Economy: specificare formato TRADE_PROPOSAL (give/receive)
- [ ] Foreign: aggiungere `proposal_type` per ACCEPT/REJECT_PROPOSAL

### Opinion Integration
- [ ] Integrare Opinion agent nel flusso di simulazione
- [ ] Collegare output a satisfaction delta

---

## 📋 Backlog

### Token Optimization
- [ ] Ridurre token count nei system prompts (~350 → ~250)
- [ ] Comprimere doctrines/policies

### President Role Enhancement
- [ ] Definire meglio PRESIDENT_OVERRIDE workflow
- [ ] President approva/modifica azioni dei ministri

---

## 📌 Design Notes

**System vs Input Prompts:**
- **System**: Identità, regole, format output (STATICO)
- **Input**: Turno, budget, risorse, relazioni (DINAMICO per turno)

**Action Limits:**
- Defense: MAX 3 azioni/turno
- Economy: MAX 1 azione/turno
- Foreign: MAX 1 azione/turno