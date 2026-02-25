"""
XAI (Explainability) Package — Counterfactual Analysis Toolkit.

Provides tools for understanding and explaining agent behavior through
post-hoc analysis and counterfactual experimentation.

Current Capabilities (embedded across other packages):
    1. Prompt Traces: Every CountryEnvelope stores full system_prompt,
       input_prompt, and raw_json for all 5 agent types (President,
       DefenseMinister, EconomicMinister, ForeignMinister, OpinionAgent).
       Enables prompt-level review of any decision at any turn.

    2. XAI Injections: SimulationEngine.fork() creates a parallel timeline.
       Injections are natural language instructions appended to agent prompts
       (e.g., "You MUST declare war on Ferecia"). Can target individual
       ministers or the president. Fork diverges from base timeline,
       enabling counterfactual analysis via DeltaAnalyzer.

    3. Deception Analysis: DeceptionAnalyzer compares public vs private
       intents using hand-crafted matrices, providing per-turn deception
       scores and identifying moral washing patterns.

    4. Divergence Scoring: DeltaAnalyzer.calculate_divergence_score()
       with weighted metrics. LLM-powered causal explanation via
       explain_divergence().

Implementation locations:
    - geomas.agents.schemas.protocol (CountryEnvelope trace fields)
    - geomas.analysis.comparison (DeltaAnalyzer)
    - geomas.analysis.deception (DeceptionAnalyzer)
    - geomas.simulation.engine (forking mechanism)

Note:
    This package is a placeholder for future dedicated XAI tools.
    Current explainability features are distributed across the codebase.
"""
