"""
Agents Package — The Cognitive Layer.

Contains the AI agent architecture for nation decision-making. Each nation
is governed by a hierarchical "Cabinet" that mirrors real-world political
structures: specialist Ministers propose, the President decides.

Architecture:
    The cognitive loop for each nation each turn:
    1. Three Ministers (Defense, Economy, Foreign) propose actions CONCURRENTLY
       via async LLM calls. Each minister has a domain-specific system prompt
       (persona, rules, available actions) and a dynamic input prompt (current
       world state, relationships, events, past actions, presidential feedback).
    2. The President LLM receives a CabinetBriefing (all 3 proposals) and
       issues a PresidentialDecree: APPROVE or VETO each domain. A VETO
       results in an IDLE action for that domain (no spending).
    3. The NationAgent constructs a CountryEnvelope from the decree,
       containing public/private/action layers plus full prompt traces.
    4. After all nations act, an OpinionAgent (population voice) reacts to
       government actions and world events, outputting multipliers (0.1-2.0)
       that modulate satisfaction changes.

Classes:
    - NationAgent (nation_agent.py, 484 lines): The main agent representing
      a nation's leadership. Orchestrates the Cabinet (Ministers) and the
      President. Manages XAI injections, async cabinet phase, presidential
      decision, and envelope construction. Stores full trace_history for
      post-hoc explainability across all turns.

    - DefenseMinister (ministers.py): Proposes military strategy. System
      prompt includes available units, terrain constraints, combat rules,
      movement ranges, and nuclear doctrine. Input prompt includes military
      deployment map, border threats, war status, and past defense actions.

    - EconomicMinister (ministers.py): Proposes economic strategy. System
      prompt includes welfare formula, war tax rules, trade constraints.
      Input prompt includes resource balances, consumption rates, trade
      opportunities, and past economic actions.

    - ForeignMinister (ministers.py): Proposes diplomatic strategy. System
      prompt includes alliance tiers, trust mechanics, message types.
      Input prompt includes trust matrix, relationship states, pending
      proposals, diplomatic history, and past foreign actions.

    - BaseMinister (ministers.py): Abstract base with prompt caching,
      memory context injection from ContextManager, and sync/async propose.

    - OpinionAgent (opinion.py, 351 lines): LLM-driven population reaction.
      Runs POST-EXECUTION and returns multipliers that modulate how
      satisfaction changes are applied. Has a deterministic fallback when
      LLM is unavailable, using cultural traits (e.g., Nationalist = 1.3x
      military sensitivity, Pacifist = 1.5x negative war reaction).

    - LLMClient (llm_client.py, 578 lines): Type-safe wrapper for LLM
      interactions using Instructor (structured output validation) and
      LiteLLM (model abstraction). Supports multiple providers:
      Azure OpenAI, Anthropic Claude (with prompt caching), Grok-4,
      DeepSeek-V3. Features: automatic retries with backoff, token usage
      logging, reasoning token extraction, raw content capture for XAI.

Subpackages:
    - schemas/: Communication protocol models
        GlobalStrategy: TOTAL_EXPANSIONISM, ARMED_ISOLATIONISM,
                       COALITION_BUILDER, SCORCHED_EARTH
        GovernmentType: DEMOCRACY, AUTHORITARIAN, THEOCRACY (affects
                       narrative framing, not mechanical rules)
        Intent types: DefenseIntentType (DETERRENCE, CONQUEST, DEFENSE,
                     IDLE, EXPORT_DEMOCRACY, HOLY_WAR),
                     ForeignIntentType (COOPERATION, COERCION, APPEASEMENT,
                     IDLE, EXPORT_DEMOCRACY, DIVINE_MANDATE)
        CountryEnvelope: The key data structure with ~100 fields:
            - Strategic layer: GlobalStrategy orientation
            - Public layer: public_statement + public intents (visible)
            - Private layer: private intents + reasoning (hidden, for XAI)
            - Action layer: typed payloads (ground truth for execution)
            - Trace layer: system/input prompts + raw JSON for all agents
        dynamic.py: Dynamic schema builder for minister responses

    - context/: Prompt construction and memory management
        system/: Static system prompts for President, Defense, Economy,
                Foreign, Opinion agents (persona + rules + action catalog)
        input/: Dynamic input builders generating natural language from
               WorldState (military deployment, resource balances, trust
               matrix, relationship states, events, proposals)
        events/: ContextManager (1058 lines) — bounded rationality memory
                with configurable token budget (default 4200 tokens),
                relationship tracking with trust trends, event extraction
                from envelopes, action history logging, presidential
                feedback (past APPROVE/VETO decisions), and automatic
                pruning to stay within budget.
        spatial.py: SpatialTranslator — converts Voronoi geography into
                   natural language for agent comprehension
        military.py: MilitaryTranslator (34KB) — generates detailed
                    military deployment context including border threats,
                    frontline analysis, naval positions, and air bases
        tokens.py: TokenCounter utility for prompt budget management
"""

from geomas.agents.nation_agent import NationAgent
from geomas.agents.ministers import DefenseMinister, EconomicMinister, ForeignMinister
from geomas.agents.llm_client import LLMClient

__all__ = [
    "NationAgent",
    "DefenseMinister", 
    "EconomicMinister",
    "ForeignMinister",
    "LLMClient"
]
