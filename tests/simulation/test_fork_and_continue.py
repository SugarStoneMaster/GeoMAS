"""
Tests for SimulationEngine.fork_and_continue().

Validates:
1. Turn semantics: snapshot(T) = world after T-1 → next turn to execute is T
2. Correct step count calculation: n_turns = max_turn(source) - fork_at_turn
3. Explicit n_turns override works
4. scenario_trigger forwarded to every step
5. injections forwarded to every step
6. n_turns=0 edge case (no steps executed)
"""
import pytest
from unittest.mock import MagicMock, patch, call
from geomas.simulation.engine import SimulationEngine


@pytest.fixture
def temp_db(tmp_path):
    from geomas.db.connection import SimulationDB
    db_file = tmp_path / "test_fac.duckdb"
    db = SimulationDB(str(db_file))
    db.initialize()
    yield db
    db.close()


@pytest.fixture
def minimal_engine(temp_db):
    """SimulationEngine with mocked agents and no real LLM."""
    with patch("geomas.agents.nation_agent.NationAgent.act"):
        engine = SimulationEngine(
            map_seed=42,
            history_seed=99,
            n_cells=50,
            n_nations=2,
            db_path=temp_db.db_path,
        )
    return engine, temp_db


# ---------------------------------------------------------------------------
# 1. Turn Semantics
# ---------------------------------------------------------------------------

class TestTurnSemantics:

    def test_snapshot_at_T_means_next_exec_is_T(self, temp_db):
        """
        After load_state(T), world.turn == T.
        This confirms snapshot(T) = post-T-1 state, and T is the next turn to run.
        """
        with patch("geomas.agents.nation_agent.NationAgent.act"):
            engine = SimulationEngine(
                map_seed=42, history_seed=99, n_cells=50, n_nations=2,
                db_path=temp_db.db_path,
            )
        source_id = engine.simulation_id

        # Manually inject a snapshot at turn 5 into the DB
        from geomas.db.serialization import serialize_world_snapshot
        engine.world.turn = 5
        snap = serialize_world_snapshot(engine.world, engine.context_manager)
        temp_db.save_snapshot(source_id, 5, **snap)

        # Load the state at turn 5
        engine.load_state(5, from_simulation_id=source_id)

        # The next turn to execute must be 5
        assert engine.world.turn == 5, (
            "After load_state(5), world.turn must be 5 since snapshot(5) = post-T4 state"
        )
        engine.close()

    def test_fork_at_turn_T_label_is_correct(self, temp_db):
        """Fork's auto-name includes @T{fork_at_turn} for clarity."""
        with patch("geomas.agents.nation_agent.NationAgent.act"):
            engine = SimulationEngine(
                map_seed=42, history_seed=99, n_cells=50, n_nations=2,
                db_path=temp_db.db_path,
            )
        source_id = engine.simulation_id

        # Save a snapshot at turn 3
        from geomas.db.serialization import serialize_world_snapshot
        engine.world.turn = 3
        snap = serialize_world_snapshot(engine.world, engine.context_manager)
        temp_db.save_snapshot(source_id, 3, **snap)

        with patch.object(engine, "run"):  # Don't actually run
            new_id = engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=3,
                n_turns=0,
            )

        info = temp_db.get_simulation_info(new_id)
        assert "@T3" in info["name"]
        engine.close()


# ---------------------------------------------------------------------------
# 2. Step Count Auto-Computation
# ---------------------------------------------------------------------------

class TestStepCount:

    def test_n_turns_auto_computes_from_source_max(self, temp_db):
        """
        When n_turns is None, steps = max_turn(source) - fork_at_turn.
        """
        with patch("geomas.agents.nation_agent.NationAgent.act"):
            engine = SimulationEngine(
                map_seed=42, history_seed=99, n_cells=50, n_nations=2,
                db_path=temp_db.db_path,
            )
        source_id = engine.simulation_id

        # Simulate a source sim with max_turn = 10
        from geomas.db.serialization import serialize_world_snapshot
        for t in range(1, 11):
            engine.world.turn = t
            snap = serialize_world_snapshot(engine.world, engine.context_manager)
            temp_db.save_snapshot(source_id, t, **snap)

        engine.world.turn = 5  # Reset to fork point

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=5,  # n_turns not specified → should be 10 - 5 = 5
            )
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("steps") == 5 or call_kwargs.args[0] == 5
        engine.close()

    def test_explicit_n_turns_overrides_auto(self, temp_db):
        """Explicit n_turns takes priority over auto-computation."""
        with patch("geomas.agents.nation_agent.NationAgent.act"):
            engine = SimulationEngine(
                map_seed=42, history_seed=99, n_cells=50, n_nations=2,
                db_path=temp_db.db_path,
            )
        source_id = engine.simulation_id

        from geomas.db.serialization import serialize_world_snapshot
        for t in [1, 5, 20]:  # source max_turn = 20; snapshot at 5 needed for load_state
            engine.world.turn = t
            snap = serialize_world_snapshot(engine.world, engine.context_manager)
            temp_db.save_snapshot(source_id, t, **snap)

        engine.world.turn = 5

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=5,
                n_turns=3,  # Explicit → must ignore 20 - 5 = 15
            )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        steps = call_kwargs.kwargs.get("steps", call_kwargs.args[0] if call_kwargs.args else None)
        assert steps == 3
        engine.close()

    def test_n_turns_zero_no_run(self, temp_db):
        """n_turns=0 must skip run() entirely."""
        with patch("geomas.agents.nation_agent.NationAgent.act"):
            engine = SimulationEngine(
                map_seed=42, history_seed=99, n_cells=50, n_nations=2,
                db_path=temp_db.db_path,
            )
        source_id = engine.simulation_id

        from geomas.db.serialization import serialize_world_snapshot
        engine.world.turn = 2
        snap = serialize_world_snapshot(engine.world, engine.context_manager)
        temp_db.save_snapshot(source_id, 2, **snap)

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=2,
                n_turns=0,
            )

        mock_run.assert_not_called()
        engine.close()


# ---------------------------------------------------------------------------
# 3. Scenario and Injection Forwarding
# ---------------------------------------------------------------------------

class TestParameterForwarding:

    def test_scenario_trigger_forwarded_to_run(self, temp_db):
        """scenario_trigger must be passed through to run()."""
        with patch("geomas.agents.nation_agent.NationAgent.act"):
            engine = SimulationEngine(
                map_seed=42, history_seed=99, n_cells=50, n_nations=2,
                db_path=temp_db.db_path,
            )
        source_id = engine.simulation_id

        from geomas.db.serialization import serialize_world_snapshot
        engine.world.turn = 2
        snap = serialize_world_snapshot(engine.world, engine.context_manager)
        temp_db.save_snapshot(source_id, 2, **snap)

        scenario = {"type": "PANDEMIA", "turn": 3}

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=2,
                n_turns=2,
                scenario_trigger=scenario,
            )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        passed_trigger = call_kwargs.kwargs.get("scenario_trigger")
        assert passed_trigger == scenario
        engine.close()

    def test_injections_forwarded_to_run(self, temp_db):
        """injections must be passed through to run()."""
        with patch("geomas.agents.nation_agent.NationAgent.act"):
            engine = SimulationEngine(
                map_seed=42, history_seed=99, n_cells=50, n_nations=2,
                db_path=temp_db.db_path,
            )
        source_id = engine.simulation_id

        from geomas.db.serialization import serialize_world_snapshot
        engine.world.turn = 2
        snap = serialize_world_snapshot(engine.world, engine.context_manager)
        temp_db.save_snapshot(source_id, 2, **snap)

        injections = [{"nation_id": "N1", "role": "DEFENSE", "action": "STRIKE", "type": "FORCE"}]

        with patch.object(engine, "run") as mock_run:
            engine.fork_and_continue(
                source_simulation_id=source_id,
                fork_at_turn=2,
                n_turns=1,
                injections=injections,
            )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        passed_inj = call_kwargs.kwargs.get("injections")
        assert passed_inj == injections
        engine.close()
