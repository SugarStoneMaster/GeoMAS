# 🏃 Active Sprint: Phase 2 (The Cognitive Layer)

**Obiettivo:** Dare vita alle nazioni implementando l'architettura Neuro-Simbolica degli Agenti.

## ✅ Completed (Phase 1)
- [x] World Engine (Voronoi, Resources, Capitals).
- [x] Spatial Graph & Pathfinding.
- [x] Spatial Translator (Intelligence Reports).
- [x] Genesis Module (History & Trust Matrix).
- [x] Visualization Dashboard.

## 📝 To-Do List (Phase 2)

### 1. LLM Infrastructure (`geomas/agents/llm_client.py`)
- [ ] Configurare `LiteLLM` o `Instructor` per Azure OpenAI.
- [ ] Creare una funzione wrapper `query_agent(prompt, response_model)` che garantisce output JSON validato da Pydantic.
- [ ] Gestire retry e fallback in caso di errori di parsing.

### 2. Cognitive Schemas (`geomas/schemas/agent_schemas.py`)
*Dalla Roadmap 2.1*
- [ ] Definire `GlobalStrategy` (Enum).
- [ ] Definire `DiplomaticEnvelope` (Struttura complessa con Public/Private Intent).
- [ ] Definire `MilitaryPayload` (Waterfall Logic).

### 3. Agent Architecture (`geomas/agents/nation_agent.py`)
*Dalla Roadmap 2.2*
- [ ] Creare la classe `NationAgent`.
- [ ] Implementare il metodo `perceive_world()`: Raccoglie dati spaziali, risorse e storia.
- [ ] Implementare il metodo `consult_ministers()`: Simula (o chiama) i ministri.
- [ ] Implementare il metodo `decide()`: Il Presidente genera l'Envelope finale.

### 4. Prompt Engineering (`geomas/agents/prompts.py`)
- [ ] Creare template Jinja2 per:
    - [ ] **System Prompt:** Inietta Persona, Strategia e Intelligence Report.
    - [ ] **Context Injection:** Filtra la storia rilevante (Genesis logs).
    - [ ] **Task Prompt:** Richiede l'azione nel formato JSON specifico.

---
**Nota:** Al termine di questo sprint, avremo un agente capace di "vedere" il mondo e produrre un output decisionale complesso e strutturato.