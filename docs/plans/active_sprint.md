# 🚀 Sprint: Fase 7.5 - Deception Detection Framework

**Status:** In Progress
**Obiettivo:** Misurare deception tra dichiarazioni pubbliche e intenzioni private

---

## 📋 Task Breakdown

### 1. Protocol Refactor (`geomas/agents/schemas/protocol.py`) ✅
- [x] Aggiungere per Defense:
  - `defense_public_intent: DefenseIntentType`
  - `defense_private_intent: DefenseIntentType`
  - `defense_private_reasoning: str`
- [x] Aggiungere per Economic:
  - `economic_public_intent: EconomicIntentType`
  - `economic_private_intent: EconomicIntentType`
  - `economic_private_reasoning: str`
- [x] Aggiungere per Foreign:
  - `foreign_public_intent: ForeignIntentType`
  - `foreign_private_intent: ForeignIntentType`
  - `foreign_private_reasoning: str`
- [x] Mantenere `GlobalStrategy` e `public_statement`
- [x] Rimuovere campi obsoleti (`PublicIntent` enum, vecchi Intent objects)

### 2. Intent Enums Audit ✅
- [x] Review `DefenseIntentType`: DETERRENCE, CONQUEST, DEFENSE, RECONNAISSANCE, PUNISHMENT, IDLE
- [x] Review `EconomicIntentType`: GROWTH, SABOTAGE, SUPPORT, SURVIVAL, IDLE
- [x] Review `ForeignIntentType`: COOPERATION, COERCION, DECEPTION, APPEASEMENT, IDLE
- [x] Aggiunto commenti esplicativi per ogni valore

### 3. Deception Matrix (`geomas/analysis/deception.py`) ✅
- [x] Definire `DEFENSE_DECEPTION_MATRIX[private][public] -> float`
- [x] Definire `ECONOMIC_DECEPTION_MATRIX[private][public] -> float`
- [x] Definire `FOREIGN_DECEPTION_MATRIX[private][public] -> float`
- [x] Implementare `calculate_domain_deception(private, public, domain)`
- [x] Implementare `calculate_score(envelope) -> float`
- [x] Implementare `calculate_detailed_score(envelope) -> dict`

### 4. Deception Tracker
- [ ] Creare `DeceptionRecord` dataclass
- [ ] Creare `DeceptionTracker` class con:
  - `log_turn(envelope, executed_actions)`
  - `get_nation_history(nation_id)`
  - `get_turn_summary(turn)`

### 5. Tests ✅
- [x] Test protocol con nuovi campi
- [x] Test deception matrix scores
- [ ] Test tracker accumulation
- [ ] Test coherence scores

### 6. Strategic Coherence (`geomas/analysis/deception.py`)
- [ ] Definire `EXPECTED_INTENTS[GlobalStrategy] -> List[IntentType]` per dominio
- [ ] Implementare `calculate_coherence_score(strategy, private_intents)`
- [ ] Coherence = quanto private intents matchano la GlobalStrategy

---

## 📌 Notes
- `public_statement` è un singolo messaggio con sezioni per ogni dominio
- Altri agenti vedono solo: `public_statement` + azioni eseguite
- `private_intent` e `private_reasoning` sono nascosti
- Il calcolo deception è deterministico (matrice predefinita)
- Coherence misura strategia vs azioni, indipendente da deception