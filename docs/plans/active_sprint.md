# 🚀 Sprint Corrente: System Prompt Refinement

**Status:** In Progress | **Test:** 400 passati (Unit + E2E + UI)

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

## ✅ Completed This Sprint

### System Prompt Fixes ✅
- [x] Defense: aggiungere `unit_type` a MOVE_TROOPS
- [x] Economy: specificare formato TRADE_PROPOSAL (give/receive)
- [x] Foreign: aggiungere `proposal_type` per ACCEPT/REJECT_PROPOSAL

### Opinion Integration ✅
- [x] Integrare Opinion agent nel flusso di simulazione
- [x] Collegare output a satisfaction delta (multiplier_increase/decrease)

---

## 📋 Backlog

### President Role Enhancement (DONE)
- [x] Definire workflow di approvazione/modifica (President as Gatekeeper via Decree)
- [x] Implementare logica `PRESIDENT_VETO` (NationAgent refactored to Approve/Veto only)
- [x] Aggiungere step di "Cabinet Meeting" nel ciclo di simulazione (Briefing -> Decree -> Envelope)
- [x] Testare override scenarios (Updated tests/agents/test_nation_agent.py)

### Next Steps
- [ ] Monitoraggio Token Usage in live run
- [ ] UI Dashboard refinement
---

## 📌 Design Notes

**System vs Input Prompts:**
- **System**: Identità, regole, format output (STATICO)
- **Input**: Turno, budget, risorse, relazioni (DINAMICO per turno)

**Action Limits:**
- Defense: MAX 3 azioni/turno
- Economy: MAX 1 azione/turno
- Foreign: MAX 1 azione/turno