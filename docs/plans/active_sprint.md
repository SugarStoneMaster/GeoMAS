# 🚀 Sprint: Fase 5 - Diplomacy & Treaty System

**Durata prevista:** ~2-3 sessioni
**Obiettivo:** Trattati, alleanze, guerra e pace

---

## 📋 Task Breakdown

#### 1. Relationship States
- [x] Definire `RelationshipState` enum: `PEACE`, `WAR`, `ALLIANCE`
- [x] Aggiungere `relationship_matrix` a `WorldState`
- [x] Default: PEACE tra tutte le nazioni
- [x] Test relationships

#### 2. SEND_DIPLOMATIC_MESSAGE Action
- [x] Definire `DiplomaticMessageType`: `PRAISE`, `THREAT`, `INSULT`
- [x] Impatti trust:
  - PRAISE: trust +0.1
  - THREAT: trust -0.3
  - INSULT: trust -0.1
- [x] Log pubblico (vedere nel turno successivo)
- [x] Test messages

#### 3. PROPOSE_ALLIANCE Action
- [x] Validazione: trust minimo (>0.6)
- [x] Pendente fino a risposta (auto-accept per ora)
- [x] Se accettata: relationship → ALLIANCE
- [x] Bonus: mutual defense
- [x] Test alliance

#### 4. DECLARATION_OF_WAR Action
- [x] Effetti: relationship → WAR
- [x] Trust → 0 tra i due
- [x] Notifica a tutti (log pubblico)
- [x] Test war declaration

#### 5. BREAK_TREATY Action
- [x] Rompere alleanza: relationship → PEACE
- [x] Trust penalty: -0.5 per chi rompe
- [x] Test break treaty

#### 6. REQUEST_PEACE Action
- [x] Solo se in WAR
- [x] Se accettata: relationship → PEACE (auto-accept per ora)
- [x] Test peace request

---

## 📌 Note

> **Focus:** Iniziare con Relationship States e DiplomaticMessage, poi le actions più complesse.

---

## 🚧 Dependencies
- Trust Matrix (già implementata)
- Action Engine + Payload system (già implementato)