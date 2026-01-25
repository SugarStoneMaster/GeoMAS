"""
Analysis Package.

Tools for analyzing agent behavior and simulation outcomes.

Modules:
    - deception: DeceptionAnalyzer for measuring alignment between
      public statements and private intentions.

The DeceptionAnalyzer calculates a score from 0.0 (honest) to 1.0 (deceptive)
based on the gap between what an agent says publicly and what it intends privately.

Example:
    from geomas.analysis.deception import DeceptionAnalyzer
    
    score = DeceptionAnalyzer.calculate_score(envelope)
    # 0.0 = perfect alignment, 1.0 = maximum deception
"""

from geomas.analysis.deception import DeceptionAnalyzer

__all__ = ["DeceptionAnalyzer"]
