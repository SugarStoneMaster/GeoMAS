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

def test_seed_restoration_in_load_state(tmp_path):
    """Verify that map_seed and history_seed are restored when loading from DB."""
    db_file = str(tmp_path / "test_seeds.duckdb")
    
    # Create and save a simulation
    orig_map_seed = 555
    orig_hist_seed = 777
    engine = SimulationEngine(
        map_seed=orig_map_seed, 
        history_seed=orig_hist_seed, 
        n_cells=50,
        n_nations=4, 
        db_path=db_file
    )
    sim_id = engine.simulation_id
    
    # Advance 1 turn and save
    engine.step()
    engine.close()
    
    # Reload with different initial seeds in constructor
    new_engine = SimulationEngine(
        map_seed=0, 
        history_seed=0, 
        simulation_id=sim_id, 
        db_path=db_file
    )
    
    # Initially seeds might be 0 from constructor (if not careful), but load_state should fix it
    new_engine.load_state(turn=1)
    
    assert new_engine.map_seed == orig_map_seed
    assert new_engine.history_seed == orig_hist_seed
