"""
Analysis Package.

Tools for analyzing agent behavior and simulation outcomes.

Modules:
    - deception: DeceptionAnalyzer for measuring deception scores
    - coherence: CoherenceAnalyzer for measuring strategy alignment
    - tracker: BehaviorTracker for logging behavior history

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
