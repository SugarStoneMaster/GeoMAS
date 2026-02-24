import pytest
import os
import zlib
from geomas.simulation.engine import SimulationEngine
from geomas.actions.opinion.traits import generate_cultural_traits

def test_cultural_traits_population():
    """Verify that nations have cultural traits populated on startup."""
    engine = SimulationEngine(n_cells=50, n_nations=4, map_seed=42)
    
    for nation in engine.world.nations.values():
        assert len(nation.cultural_traits) >= 4
        assert len(nation.cultural_traits) <= 6
        print(f"Nation {nation.id} traits: {nation.cultural_traits}")

def test_stable_hashing_determinism():
    """Verify that traits are identical regardless of Python's hash randomization."""
    # Simulation logic now uses zlib.adler32 which is stable across processes
    seed = 12345
    nation_id = "AGRIA"
    
    # Manually calculate what we expect from the new logic
    expected_nation_seed = (seed + zlib.adler32(nation_id.encode())) & 0xFFFFFFFF
    
    traits1 = generate_cultural_traits(nation_id, seed)
    
    # Traits should match the deterministic seeding logic
    import random
    rng = random.Random(expected_nation_seed)
    from geomas.actions.opinion.traits import DEMOGRAPHIC_DISTRIBUTIONS, CULTURAL_VALUES, BEHAVIORAL_TRAITS, COGNITIVE_BIASES
    
    expected_traits = []
    expected_traits.append(rng.choice(DEMOGRAPHIC_DISTRIBUTIONS))
    expected_traits.extend(rng.sample(CULTURAL_VALUES, k=2))
    n_behavioral = rng.randint(1, 2)
    expected_traits.extend(rng.sample(BEHAVIORAL_TRAITS, k=n_behavioral))
    expected_traits.append(rng.choice(COGNITIVE_BIASES))
    
    assert traits1 == expected_traits

