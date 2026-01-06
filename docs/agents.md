# 🤖 Agent Architecture & Protocols

## 🏛️ The Hierarchical Cabinet
Ogni nazione non è un singolo LLM, ma un sistema multi-agente interno.

### Roles
1.  **Minister of Defense:** Focus su sicurezza, confini, minacce militari.
2.  **Minister of Economy:** Focus su PIL, risorse, commercio. Usa solver lineari (`scipy`) per ottimizzare le proposte.
3.  **Minister of Foreign Affairs:** Focus su alleanze, trattati, reputazione (`Trust Matrix`).
4.  **The President:** Decide quale proposta accettare o combinare.
5.  **Public Opinion:** Agente passivo/reattivo. Se la `Satisfaction` scende sotto soglia, triggera scioperi.

## 📜 Communication Protocols (Schema-First)
Tutta la comunicazione deve avvenire tramite oggetti **Pydantic**. Niente testo libero non strutturato.

### 1. Diplomatic Envelope
Il formato standard per le azioni tra nazioni.
```python
class DiplomaticEnvelope(BaseModel):
    sender_id: str
    target_id: str
    public_statement: str  # Quello che viene detto pubblicamente (può essere una bugia)
    private_intent: Literal["Sincere", "Bluff", "Threat"]
    payload: ActionPayload # L'azione reale da eseguire
```

### 2. Action Payload
```python
class ActionPayload(BaseModel):
    action_type: Literal["TRADE", "WAR", "ALLIANCE", "SANCTION"]
    parameters: Dict[str, Any] # Es. {"amount": 100, "resource": "OIL"}
```

## 🧠 LLM Interaction Strategy
*   Usa `LiteLLM` o `Instructor` per forzare l'output JSON.
*   **Context Injection:** Non passare tutto lo stato del mondo. Passa solo ciò che la nazione *sa* (Fog of War).
*   **Prompting:** Usa "Persona Prompting" per definire i tratti (es. "Sei un Ministro della Difesa Paranoico").