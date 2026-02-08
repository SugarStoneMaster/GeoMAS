"""
UI Component Tests.

Tests that the web UI components can be imported and render without errors.
Run with: pytest tests/web/test_ui.py -v
"""

import pytest
import sys
import os
import importlib.util

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from geomas.simulation import SimulationEngine


def import_module_from_path(module_name: str, file_path: str):
    """Dynamically import a module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Pre-import web modules using absolute paths
WEB_DIR = os.path.join(project_root, "web")

mock_client_module = import_module_from_path(
    "web.mock_client", 
    os.path.join(WEB_DIR, "mock_client.py")
)
UIMockLLM = mock_client_module.UIMockLLM


class TestUIComponents:
    """Tests for individual UI components."""
    
    @pytest.fixture
    def world(self):
        """Create a test world."""
        sim = SimulationEngine(
            map_seed=42,
            history_seed=99,
            n_cells=100,
            llm_client=UIMockLLM()
        )
        return sim.world
    
    def test_mock_client_defense_proposal(self):
        """Test that mock client returns valid DefenseProposal."""
        from geomas.agents.schemas import DefenseProposal
        
        client = UIMockLLM()
        result = client.query_agent("", "", DefenseProposal)
        
        assert isinstance(result, DefenseProposal)
        assert result.urgency == 1
    
    def test_mock_client_country_envelope(self):
        """Test that mock client returns valid CountryEnvelope."""
        from geomas.agents.schemas import CountryEnvelope
        
        client = UIMockLLM()
        result = client.query_agent("", "", CountryEnvelope)
        
        assert isinstance(result, CountryEnvelope)
        assert result.public_statement is not None
    
    def test_map_renderer_darken_color(self):
        """Test the darken_color utility function."""
        map_renderer = import_module_from_path(
            "web.components.map_renderer",
            os.path.join(WEB_DIR, "components", "map_renderer.py")
        )
        
        darker = map_renderer.darken_color("#ffffff", factor=0.5)
        assert darker == "#808080"


class TestUIIntegration:
    """Integration tests for the full UI flow."""
    
    def test_simulation_with_mock_client(self):
        """Test that simulation runs with mock client."""
        sim = SimulationEngine(
            map_seed=42,
            history_seed=99,
            n_cells=100,
            llm_client=UIMockLLM()
        )
        
        # Run a turn
        sim.step()
        
        assert sim.world.turn == 2
        assert len(sim.history) == 1
        assert len(sim.history[0]) > 0  # At least one envelope
    
    def test_deception_analysis_with_mock(self):
        """Test that deception analysis works with mock data."""
        from geomas.analysis.deception import DeceptionAnalyzer
        
        sim = SimulationEngine(
            map_seed=42,
            history_seed=99,
            n_cells=100,
            llm_client=UIMockLLM()
        )
        sim.step()
        
        # Analyze first envelope
        envelope = sim.history[0][0]
        score = DeceptionAnalyzer.calculate_score(envelope)
        
        # Mock client returns PEACEFUL public + IDLE military = honest
        assert 0.0 <= score <= 1.0
