"""
Analysis Package — Behavioral Intelligence Suite.

Tools for analyzing agent behavior and simulation outcomes. This package
provides quantitative metrics that bridge the gap between raw agent actions
and research-grade observables for thesis analysis.

Modules:
    - deception.py (197 lines): DeceptionAnalyzer
      Core analyzer computing deception scores by comparing public_intent
      vs private_intent per domain. Uses two hand-crafted matrices:
        DEFENSE_MATRIX: 30+ entries mapping (private, public) intent pairs
          to deception scores (0.0 honest → 1.0 max deception).
          Example: (CONQUEST, DEFENSE) = 0.9, (CONQUEST, IDLE) = 0.95.
          Includes governance-specific moral washing patterns:
          - EXPORT_DEMOCRACY: Democracies framing conquest as liberation (0.95)
          - HOLY_WAR: Theocracies framing conquest as sacred duty (0.95)
        FOREIGN_MATRIX: 30+ entries for diplomatic deception.
          Example: (COERCION, COOPERATION) = 0.85 (backstabbing).
          Includes DIVINE_MANDATE for theocratic diplomatic framing.
      Aggregation: total = average(defense_score, foreign_score).
      Economic domain excluded — actions are directly observable and
      lack the narrative framing needed for moral washing measurement.

    - coherence.py (75 lines): CoherenceAnalyzer
      Measures how well private intents align with declared GlobalStrategy.
      Each strategy has "expected" intent sets:
        TOTAL_EXPANSIONISM expects CONQUEST/DETERRENCE + COERCION
        ARMED_ISOLATIONISM expects DEFENSE/DETERRENCE + IDLE/APPEASEMENT
        COALITION_BUILDER expects DEFENSE/DETERRENCE + COOPERATION
        SCORCHED_EARTH expects CONQUEST/DEFENSE + COERCION
      Score = matches / 2.0 (0.0 incoherent → 1.0 perfectly aligned).

    - tracker.py (134 lines): BehaviorTracker
      Accumulates BehaviorRecord dataclasses per nation per turn.
      Provides: get_nation_history(), get_turn_summary(),
      get_nation_average(), get_most_deceptive_nations(limit).
      Dual indexing: by nation_id (chronological) and by turn (cross-nation).

    - comparison.py (185 lines): DeltaAnalyzer
      Counterfactual divergence analysis for XAI fork-and-compare:
        compare_worlds(): Per-nation deltas (satisfaction, power, resources,
          military) + global deltas (trust divergence, relationship changes).
        compare_timelines(): Step-by-step delta series.
        calculate_divergence_score(): Weighted scalar (W_SAT=1.0, W_POWER=0.1,
          W_TRUST=0.5, W_REL=50.0) for quick divergence magnitude.
        explain_divergence(): LLM-powered natural language explanation of
          causal chain from XAI injection to observed deltas.

    - sanity.py (98 lines): SimulationHealthAnalyzer
      Post-simulation health report analyzing:
        Economic stability (budget mean, volatility coefficient, trend)
        Social stability (satisfaction final/min/max, trend classification)
        Resource balance (global food/energy trends)
      Generates formatted text report with status icons (✅/❌/⚠️).

    - token_logger.py (87 lines): TokenLogger
      Global singleton accumulating TokenUsageEntry records (Pydantic).
      Fields: timestamp, turn, nation_id, role, model, input/output/total/
      reasoning_tokens. Flushes to CSV on simulation close.

Example:
    from geomas.analysis import DeceptionAnalyzer, CoherenceAnalyzer

    deception = DeceptionAnalyzer.calculate_score(envelope)
    coherence = CoherenceAnalyzer.calculate_score(strategy, ...)
"""

from geomas.analysis.deception import DeceptionAnalyzer
from geomas.analysis.coherence import CoherenceAnalyzer
from geomas.analysis.tracker import BehaviorRecord, BehaviorTracker

__all__ = [
    "DeceptionAnalyzer",
    "CoherenceAnalyzer",
    "BehaviorRecord",
    "BehaviorTracker",
]
