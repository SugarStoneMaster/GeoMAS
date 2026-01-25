"""
Core Package.

Contains foundational simulation components that don't fit elsewhere:

Modules:
    - genesis: Historical simulation engine that generates plausible
      nation histories through simulated conflicts and territory changes.
      
The GenesisEngine runs before the main simulation to establish:
    - Initial trust relationships between nations
    - Historical events that shape agent memories
    - Realistic territorial distributions

Note:
    The GenesisEngine uses its own RNG (history_seed) separate from
    the map generation seed to ensure reproducibility.
"""

from geomas.core.genesis import GenesisEngine

__all__ = ["GenesisEngine"]
