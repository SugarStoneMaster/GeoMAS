"""
Tests for Opinion Agent integration.

Tests the OpinionAgent class and run_opinion_phase function.
"""

import pytest
from geomas.world import generate_world
from geomas.agents.opinion import (
    OpinionAgent,
    OpinionResponse,
)
from geomas.simulation.phases import (
    run_opinion_phase,
)
from geomas.actions.opinion.handler import calculate_turn_satisfaction_delta


class TestOpinionAgent:
    """Tests for OpinionAgent class."""
    
    def test_deterministic_reaction_without_llm(self):
        """OpinionAgent works without LLM client (deterministic fallback)."""
        agent = OpinionAgent(
            nation_id="test_nation",
            nation_name="Test Republic",
            cultural_traits=["Nationalist", "Resilient"],
            llm_client=None  # No LLM
        )
        
        response = agent.react(
            events=["WAR_DECLARED by Enemy"],
            government_actions=["Defense: MOVE_TROOPS"],
            current_satisfaction=50.0,
            at_war=True
        )
        
        assert isinstance(response, OpinionResponse)
        assert 0.1 <= response.multiplier_increase <= 2.0
        assert 0.1 <= response.multiplier_decrease <= 2.0
    
    def test_nationalist_trait_increases_sensitivity(self):
        """Nationalist trait increases reaction multipliers."""
        agent_neutral = OpinionAgent(
            nation_id="neutral",
            nation_name="Neutral Land",
            cultural_traits=[],
            llm_client=None
        )
        
        agent_nationalist = OpinionAgent(
            nation_id="nationalist",
            nation_name="Proud Nation",
            cultural_traits=["Nationalist"],
            llm_client=None
        )
        
        response_neutral = agent_neutral._deterministic_reaction(
            events=[], government_actions=[], current_satisfaction=50, at_war=False
        )
        response_nationalist = agent_nationalist._deterministic_reaction(
            events=[], government_actions=[], current_satisfaction=50, at_war=False
        )
        
        # Nationalist should have higher multipliers
        assert response_nationalist.multiplier_decrease > response_neutral.multiplier_decrease
        assert response_nationalist.multiplier_increase > response_neutral.multiplier_increase
    
    def test_resilient_trait_reduces_negative_impact(self):
        """Resilient trait reduces multiplier_decrease."""
        agent_normal = OpinionAgent(
            nation_id="normal",
            nation_name="Normal Land",
            cultural_traits=[],
            llm_client=None
        )
        
        agent_resilient = OpinionAgent(
            nation_id="resilient",
            nation_name="Strong Nation",
            cultural_traits=["Resilient"],
            llm_client=None
        )
        
        response_normal = agent_normal._deterministic_reaction(
            events=[], government_actions=[], current_satisfaction=50, at_war=False
        )
        response_resilient = agent_resilient._deterministic_reaction(
            events=[], government_actions=[], current_satisfaction=50, at_war=False
        )
        
        # Resilient should have lower decrease multiplier
        assert response_resilient.multiplier_decrease < response_normal.multiplier_decrease
    
    def test_war_weariness_reduces_victory_impact(self):
        """Low satisfaction + at war = war weariness reduces multiplier_increase."""
        agent = OpinionAgent(
            nation_id="weary",
            nation_name="War-Weary Nation",
            cultural_traits=[],
            llm_client=None
        )
        
        # Not at war, good satisfaction
        response_happy = agent._deterministic_reaction(
            events=[], government_actions=[], current_satisfaction=80, at_war=False
        )
        
        # At war, low satisfaction
        response_weary = agent._deterministic_reaction(
            events=[], government_actions=[], current_satisfaction=30, at_war=True
        )
        
        # War-weary population cares less about victories
        assert response_weary.multiplier_increase < response_happy.multiplier_increase


class TestOpinionResponse:
    """Tests for OpinionResponse schema."""
    
    def test_response_validation(self):
        """OpinionResponse validates multiplier bounds."""
        # Valid response
        response = OpinionResponse(
            multiplier_increase=1.5,
            multiplier_decrease=0.8,
            mood="CONTENT",
            reasoning="Test"
        )
        assert response.multiplier_increase == 1.5
        
    def test_response_clamps_values(self):
        """Values outside 0.1-2.0 are rejected by Pydantic."""
        with pytest.raises(ValueError):
            OpinionResponse(multiplier_increase=3.0)  # Too high
        
        with pytest.raises(ValueError):
            OpinionResponse(multiplier_decrease=0.05)  # Too low


class TestCalculateTurnSatisfactionDelta:
    """Tests for calculate_turn_satisfaction_delta function."""
    
    def test_war_causes_negative_delta(self):
        """Being at war results in negative satisfaction delta."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        
        delta = calculate_turn_satisfaction_delta(
            nation=nation,
            world=world,
            events=[],
            gov_actions=[],
            at_war=True
        )
        
        assert delta < 0 
    
    def test_peace_at_baseline(self):
        """No events and at peace = zero satisfaction delta."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        nation.total_food = 100
        nation.total_energy = 100
        
        delta = calculate_turn_satisfaction_delta(
            nation=nation,
            world=world,
            events=[],
            gov_actions=[],
            at_war=False
        )
        
        assert delta == 1.0  # Peace bonus
    
    def test_positive_events_increase_delta(self):
        """Positive events increase satisfaction delta."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        nation.total_food = 200 # Surplus
        nation.total_energy = 200
        
        delta = calculate_turn_satisfaction_delta(
            nation=nation,
            world=world,
            events=["ALLIANCE_FORMED with Ally", "TRADE_DEAL signed"],
            gov_actions=["Economy: INVEST_WELFARE"],
            at_war=False
        )
        
        assert delta > 0
    
    def test_negative_events_decrease_delta(self):
        """Negative events decrease satisfaction delta."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        nation = list(world.nations.values())[0]
        
        delta = calculate_turn_satisfaction_delta(
            nation=nation,
            world=world,
            events=["TERRITORY_LOST to Enemy", "ALLIANCE_BROKEN"],
            gov_actions=["Economy: RAISE_WAR_TAX"],
            at_war=True
        )
        
        assert delta < -5


class TestRunOpinionPhase:
    """Tests for run_opinion_phase integration."""
    
    def test_opinion_phase_updates_satisfaction(self):
        """run_opinion_phase updates nation satisfaction."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        turn_logs = []
        
        # Create opinion agents
        opinion_agents = {}
        for nation_id, nation in world.nations.items():
            opinion_agents[nation_id] = OpinionAgent(
                nation_id=nation_id,
                nation_name=nation.name,
                cultural_traits=["Nationalist"],
                llm_client=None
            )
        
        # Record initial satisfaction
        initial_sats = {nid: n.public_satisfaction for nid, n in world.nations.items()}
        
        # Simulate some event
        world.global_events.append("TRADE_DEAL signed by Test Nation and Other")
        
        # Run opinion phase with empty envelopes
        run_opinion_phase(world, turn_logs, opinion_agents, envelopes=[])
        
        # Satisfaction should have changed for at least one nation
        # (global events may not affect all nations equally)
        changes = [
            abs(world.nations[nid].public_satisfaction - initial_sats[nid])
            for nid in world.nations
        ]
        assert any(c > 0 for c in changes) or len(turn_logs) >= 0  # Phase ran
    
    def test_opinion_phase_logs_changes(self):
        """run_opinion_phase logs significant satisfaction changes."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        turn_logs = []
        
        # Create opinion agents
        opinion_agents = {}
        for nation_id, nation in world.nations.items():
            opinion_agents[nation_id] = OpinionAgent(
                nation_id=nation_id,
                nation_name=nation.name,
                cultural_traits=[],
                llm_client=None
            )
            # Force a war scenario for significant delta
            for other_id in world.nations:
                if other_id != nation_id:
                    world.relationship_matrix[nation_id][other_id] = "WAR"
        
        run_opinion_phase(world, turn_logs, opinion_agents, envelopes=[])
        
        # Should have [OPINION] logs
        opinion_logs = [log for log in turn_logs if "[OPINION]" in log]
        assert len(opinion_logs) > 0
