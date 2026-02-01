# 🚀 Sprint: Fase 6 - Public Opinion & Internal Stability

**Status:** In Progress - 142 test passano
**Obiettivo:** Popolazione come vincolo al potere tramite LLM Agent

---

## 📋 Task Breakdown

#### 1. Schema Migration ✅
- [x] Migrare `public_satisfaction` da 0.0-1.0 a 0-100
- [x] Nuovi campi NationState: `multiplier_increase`, `multiplier_decrease`, `cultural_traits`, `civil_unrest_active`

#### 2. Opinion Package ✅
- [x] `geomas/actions/opinion/` creato
- [x] `schemas.py`: OpinionPayload, OpinionTrigger, costanti
- [x] `handler.py`: execute_opinion, apply_satisfaction_deltas, check_triggers
- [x] `traits.py`: generazione tratti culturali (seed-based)
- [ ] Population Agent system prompt template

#### 3. Satisfaction Dynamics ✅
- [x] Base deltas: WAR -3, PEACE +1, deficit -2, surplus +1
- [x] Formula con moltiplicatori (increase/decrease)

#### 4. Economic Actions ✅
- [x] **INVEST_WELFARE**: `gain = 10 * log(1 + amount / 100)` (logaritmico)
- [x] **RAISE_WAR_TAX**: -15 satisfaction

#### 5. Automatic Triggers ✅
- [x] **GENERAL_STRIKE**: sat < 20 → production 50%
- [x] **CIVIL_UNREST**: sat < 10 → province 0 output
- [x] Recovery: sat > 50 termina unrest

#### 6. Population LLM Agent 🔄
- [ ] System prompt template con demographics/traits
- [ ] Input: eventi turno, decisioni governo
- [ ] Output: multiplier_increase, multiplier_decrease (0.1-2.0)

---

## 📌 Remaining
Solo LLM agent prompt template da completare.