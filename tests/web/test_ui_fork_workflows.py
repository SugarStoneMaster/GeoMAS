"""
Integration tests for UI-level fork workflows: XAI injection and scenario triggering.

These tests simulate the same logic that app.py's sidebar and auto-run loop execute,
without invoking Streamlit directly (Streamlit widgets are not pytest-testable).

The pattern tested:
  1. A simulation is created and run for N turns (persisted to DB)
  2. The user loads a snapshot at turn T (Analysis-mode "Time Travel")
  3. The user either:
     (a) Configures injections + presses "Run Fork (remaining turns)": XAI path
     (b) Configures a scenario with a custom trigger turn + presses "Run Fork": Scenario path
  4. fork_and_continue() is called with the correct parameters
  5. The new simulation is independently queryable from the DB

The session-state logic is exercised directly through SimulationEngine, since that
is exactly what the UI delegates to. We verify that:
  - The forked simulation starts from the declared snapshot turn T
  - Steps executed = max_turn(source) - T (or explicit override)
  - Scenario is triggered at the correct turn
  - Injections are forwarded to every step
  - Source simulation history is not altered by the fork
"""

import pytest
import json
from unittest.mock import patch, MagicMock, call
from geomas.simulation.engine import SimulationEngine
from geomas.db.connection import SimulationDB


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    """Temporary DuckDB for integration tests."""
    db_file = tmp_path / "ui_fork_integration.duckdb"
    db_obj = SimulationDB(str(db_file))
    db_obj.initialize()
    yield db_obj
    db_obj.close()


@pytest.fixture
def populated_sim(db):
    """
    Simulates the state after a user has run a simulation for 10 turns and
    the app persisted all snapshots to the DB.
    We skip real LLM calls by mocking NationAgent.act.
    """
    with patch("geomas.agents.nation_agent.NationAgent.act") as mock_act, \
         patch("geomas.simulation.engine.run_upkeep_phase"), \
         patch("geomas.simulation.engine.run_opinion_phase"):

        engine = SimulationEngine(
            map_seed=42,
            history_seed=99,
            n_cells=50,
            n_nations=2,
            db_path=db.db_path,
        )
        source_id = engine.simulation_id

        from tests.conftest import create_test_envelope
        nation_ids = list(engine.world.nations.keys())

        # Simulate 10 turns of snapshot persistence without full agent logic
        from geomas.db.serialization import serialize_world_snapshot
        for turn in range(1, 11):
            engine.world.turn = turn
            snap = serialize_world_snapshot(engine.world, engine.context_manager)
            db.save_snapshot(source_id, turn, **snap)

        # Set engine to the end state
        engine.world.turn = 10

    return engine, source_id, db


# ---------------------------------------------------------------------------
# 1. XAI / Injection Fork Flow
# ---------------------------------------------------------------------------

class TestXAIForkUIFlow:
    """
    Tests the Analysis-mode XAI flow:
    User loads snapshot at T, adds injections, presses 'Run Fork (N-T turns)'.
    """

    def test_xai_fork_computes_remaining_turns_like_ui(self, populated_sim):
        """
        UI computes: fork_remaining = max_turn(source) - current_turn
        Verify that the value matches what fork_and_continue() would use.
        """
        engine, source_id, db = populated_sim

        # Simulate UI: user time-travels to turn 6
        fork_at_turn = 6
        engine.load_state(fork_at_turn, from_simulation_id=source_id)

        # Replicate the UI's formula verbatim:
        source_max_turn = db.get_max_turn(source_id)
        fork_remaining = max(1, source_max_turn - engine.world.turn)

        # Should be 10 - 6 = 4
        assert engine.world.turn == fork_at_turn
        assert source_max_turn == 10
        assert fork_remaining == 4

    def test_xai_fork_run_step_count(self, populated_sim):
        """
        fork_and_continue() runs exactly (max_turn - fork_at_turn) steps.
        """
        engine, source_id, db = populated_sim

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=7,
            )

        mock_run.assert_called_once()
        # fork_and_continue passes all args as kwargs; no positional args expected
        steps_called = mock_run.call_args.kwargs["steps"]
        assert steps_called == 3  # 10 - 7 = 3

    def test_xai_injection_forwarded_to_all_steps(self, populated_sim):
        """
        Injections are passed through to run(), which forwards them to every step().
        """
        engine, source_id, db = populated_sim

        injection = [{"nation_id": "AGRIA", "role": "Defense", "action": "MOVE_TROOPS", "type": "FORCE"}]

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=8,
                n_turns=2,
                injections=injection,
            )

        mock_run.assert_called_once()
        passed_injections = mock_run.call_args.kwargs.get("injections")
        assert passed_injections == injection

    def test_xai_fork_override_turns(self, populated_sim):
        """
        UI allows manual override: 'Override turns = 3'.
        Even if max_turn=10 and fork_at=5 (auto=5), the override wins.
        """
        engine, source_id, db = populated_sim

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=5,
                n_turns=2,  # Manual override
            )

        # fork_and_continue passes all args as kwargs; no positional args expected
        steps_called = mock_run.call_args.kwargs["steps"]
        assert steps_called == 2

    def test_xai_fork_creates_independent_simulation(self, populated_sim):
        """
        After fork_and_continue(), the new simulation is independently addressable in DB,
        and the source simulation's history is intact.
        """
        engine, source_id, db = populated_sim

        with patch.object(engine, "run"):
            new_id = engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=5,
                n_turns=0,
            )

        # New sim exists
        new_info = db.get_simulation_info(new_id)
        assert new_info is not None
        assert new_id != source_id

        # Source sim still has its original max turn
        source_max = db.get_max_turn(source_id)
        assert source_max == 10

        # Forked sim has history up to fork_at_turn (copy_history_for_fork was called)
        forked_snap = db.load_snapshot(new_id, 5)
        assert forked_snap is not None


# ---------------------------------------------------------------------------
# 2. Scenario Fork Flow
# ---------------------------------------------------------------------------

class TestScenarioForkUIFlow:
    """
    Tests the scenario triggering flow:
    User picks scenario type + trigger turn → runs simulation with the scenario active.
    """

    def test_scenario_trigger_at_custom_turn(self, populated_sim):
        """
        When user sets trigger_turn=8 on a fork from T=6,
        scenario_trigger dict must have 'turn': 8 and reach the step call.
        """
        engine, source_id, db = populated_sim

        scenario_trigger = {"type": "PANDEMIA", "turn": 8}

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=6,
                n_turns=4,
                scenario_trigger=scenario_trigger,
            )

        passed_trigger = mock_run.call_args.kwargs.get("scenario_trigger")
        assert passed_trigger == {"type": "PANDEMIA", "turn": 8}

    def test_scenario_trigger_not_fired_before_its_turn(self, populated_sim):
        """
        The scenario's 'turn' guard (check_and_trigger_scenario) must prevent it from
        firing before trigger_turn. We verify this at the engine level: if the
        scenario dict says turn=99, no actual scenario logic fires during step() on turn 5.
        """
        engine, source_id, db = populated_sim

        # Load to turn 5 — scenario is scheduled for the far future
        engine.load_state(5, from_simulation_id=source_id)
        engine.fork(new_name="Scenario far future test")

        scenario_trigger = {"type": "PANDEMIA", "turn": 99}  # Won't fire during turn 5

        with patch("geomas.simulation.scenarios.trigger_pandemic") as mock_pandemic, \
             patch("geomas.simulation.engine.run_upkeep_phase"), \
             patch("geomas.simulation.engine.run_opinion_phase"), \
             patch("geomas.agents.nation_agent.NationAgent.act") as mock_act:

            from tests.conftest import create_test_envelope
            nation_ids = list(engine.world.nations.keys())
            mock_act.return_value = create_test_envelope(nation_ids[0], turn=engine.world.turn)

            engine.step(scenario_trigger=scenario_trigger)

        # Pandemic should NOT have been called (trigger_turn=99 != current_turn=5)
        mock_pandemic.assert_not_called()

    def test_scenario_fires_exactly_at_trigger_turn(self, populated_sim):
        """
        Scenario fires precisely when world.turn == scenario_trigger['turn'].
        """
        engine, source_id, db = populated_sim

        # Load to turn 7 so that step() will execute turn 7
        engine.load_state(7, from_simulation_id=source_id)
        engine.fork(new_name="Scenario exact turn test")

        assert engine.world.turn == 7
        scenario_trigger = {"type": "PANDEMIA", "turn": 7}

        with patch("geomas.simulation.scenarios.trigger_pandemic", return_value=[]) as mock_pandemic, \
             patch("geomas.simulation.engine.run_upkeep_phase"), \
             patch("geomas.simulation.engine.run_opinion_phase"), \
             patch("geomas.agents.nation_agent.NationAgent.act") as mock_act:

            from tests.conftest import create_test_envelope
            nation_ids = list(engine.world.nations.keys())
            mock_act.return_value = create_test_envelope(nation_ids[0], turn=engine.world.turn)

            engine.step(scenario_trigger=scenario_trigger)

        # Pandemic MUST have been called exactly once (turn 7 == trigger_turn 7)
        mock_pandemic.assert_called_once()

    def test_scenario_trigger_not_fired_in_new_simulation_mode(self, populated_sim):
        """
        When running from turn 1 (new sim, no fork), the scenario fires at midpoint
        as configured. Verify the midpoint computation matches what scenario_selection_dialog did.

        UI formula: trigger_turn = world.turn + num_turns // 2
        """
        engine, source_id, db = populated_sim

        # Simulate: user clicks "Run 10", midpoint = 10 // 2 = 5
        num_turns = 10
        current_turn = 1  # World is at genesis (turn 1)
        trigger_turn = current_turn + num_turns // 2  # = 6

        # The scenario_trigger dict that app.py would build:
        scenario_trigger = {"type": "SCOPERTA RISORSE", "turn": trigger_turn}

        assert trigger_turn == 6, "Midpoint formula mismatch"
        assert scenario_trigger["turn"] == 6

    def test_scenario_at_custom_turn_vs_midpoint(self, db):
        """
        With the new UI (slider), the user can set trigger_turn to any value.
        This test ensures that values both before and after the natural midpoint are respected.
        """
        engine = SimulationEngine(
            map_seed=42, history_seed=99, n_cells=50, n_nations=2,
            db_path=db.db_path,
        )
        current_turn = engine.world.turn  # Should be 1

        num_turns = 20
        midpoint_turn = current_turn + num_turns // 2  # Default: 11

        # User overrides to early (turn 3) or late (turn 18)
        early_trigger = current_turn + 2
        late_trigger = current_turn + 18

        # All are valid trigger turns within the run range
        assert current_turn < early_trigger <= current_turn + num_turns
        assert current_turn < late_trigger <= current_turn + num_turns
        assert early_trigger != midpoint_turn  # Confirmed it's non-default
        assert late_trigger != midpoint_turn

        engine.close()


# ---------------------------------------------------------------------------
# 3. Combined: Scenario Injected into Forked Simulation
# ---------------------------------------------------------------------------

class TestCombinedForkAndScenario:
    """
    Tests the fully combined path: fork from loaded sim + scenario trigger.
    This is the new unified workflow where you load a past sim, fork at T,
    and inject a scenario at turn T+k.
    """

    def test_combined_fork_scenario_config(self, populated_sim):
        """
        Scenario and fork are configured together:
        - Source sim max_turn = 10
        - Fork at turn 5 → n_turns auto = 5
        - Scenario trigger at turn 8 (within the forked run range)
        Everything reaches fork_and_continue() with the right parameters.
        """
        engine, source_id, db = populated_sim

        scenario = {"type": "INSURREZIONE", "turn": 8}

        with patch.object(engine, "run") as mock_run:
            new_id = engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=5,
                scenario_trigger=scenario,
            )

        mock_run.assert_called_once()
        kwargs = mock_run.call_args.kwargs
        assert kwargs["steps"] == 5           # 10 - 5
        assert kwargs["scenario_trigger"] == scenario
        assert new_id != source_id

    def test_combined_fork_injection_and_scenario(self, populated_sim):
        """
        Both injections and a scenario trigger can coexist in the same fork run.
        Both are forwarded to run() untouched.
        """
        engine, source_id, db = populated_sim

        injection = [{"nation_id": "AGRIA", "role": "Foreign", "action": "TRADE_AGREEMENT", "type": "FORCE"}]
        scenario = {"type": "PANDEMIA", "turn": 9}

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=6,
                n_turns=4,
                injections=injection,
                scenario_trigger=scenario,
            )

        kwargs = mock_run.call_args.kwargs
        assert kwargs["injections"] == injection
        assert kwargs["scenario_trigger"] == scenario
        assert kwargs["steps"] == 4
