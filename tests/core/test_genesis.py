import pytest
import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from geomas.world import generate_world
from geomas.world.genesis import GenesisEngine

def test_genesis_populates_trust():
    """Verify that Genesis modifies the Trust Matrix."""
    world = generate_world(seed=42, history_seed=123, n_cells=100, n_nations=10)
    
    trust_values = []
    nation_ids = list(world.nations.keys())
    for i in range(len(nation_ids)):
        for j in range(i + 1, len(nation_ids)):
            val = world.trust_matrix[nation_ids[i]][nation_ids[j]]
            trust_values.append(val)
            
    # Check variance
    assert np.std(trust_values) > 0.01, "Trust Matrix is too flat (Genesis failed to create variety)"
    assert any(v > 0.8 for v in trust_values), "No alliances formed"
    assert any(v < 0.4 for v in trust_values), "No rivalries formed"

def test_genesis_logs_events():
    """Verify that history log is populated."""
    world = generate_world(seed=42, history_seed=123, n_cells=100, n_nations=5)
    
    assert len(world.global_events) > 0
    assert "Year 1" in world.global_events[0] or "Year" in world.global_events[0]

def test_genesis_determinism():
    """Verify that same history_seed produces same Trust Matrix."""
    w1 = generate_world(seed=42, history_seed=99, n_cells=100, n_nations=5)
    w2 = generate_world(seed=42, history_seed=99, n_cells=100, n_nations=5)
    
    n_a = list(w1.nations.keys())[0]
    n_b = list(w1.nations.keys())[1]
    
    assert w1.trust_matrix[n_a][n_b] == w2.trust_matrix[n_a][n_b]
    assert w1.global_events == w2.global_events
