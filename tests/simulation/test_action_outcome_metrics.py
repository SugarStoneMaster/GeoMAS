"""
Tests for Action Outcome and Presidential Decision Metrics.

Verifies that:
- extract_action_outcomes() correctly reads engine-level execution_outcome from envelopes
- extract_presidential_decisions() correctly reads APPROVE/VETO per domain
- Both extractors return the expected shape of rows ready for MetricsDB insertion
- MetricsDB.insert_action_outcomes() and .insert_presidential_decisions() persist data
"""

import tempfile
import os
import pytest

from unittest.mock import MagicMock
from geomas.calculators.metrics import (
    extract_action_outcomes,
    extract_presidential_decisions,
)
from geomas.db.metrics_db import MetricsDB
from geomas.actions.common import Decision, ExecutionOutcome
from geomas.actions.defense.schemas import (
    DefenseActionType,
    DefenseActionItem,
    DefensePayload,
)
from geomas.actions.economy.schemas import EconomicPayload, EconomicActionType
from geomas.actions.foreign.schemas import ForeignPayload, ForeignActionType
from geomas.agents.schemas import GlobalStrategy
from geomas.agents.schemas.protocol import GovernmentType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_envelope(
    *,
    nation_id: str = "nation_a",
    defense_moves: list | None = None,
    eco_action_type: EconomicActionType | None = EconomicActionType.INVEST_WELFARE,
    for_action_type: ForeignActionType | None = ForeignActionType.IDLE,
    defense_decision: Decision = Decision.APPROVE,
    eco_decision: Decision = Decision.APPROVE,
    for_decision: Decision = Decision.APPROVE,
    eco_outcome: ExecutionOutcome | None = None,
    for_outcome: ExecutionOutcome | None = None,
) -> MagicMock:
    """Build a minimal envelope mock for unit testing the extractors."""
    env = MagicMock()
    env.sender_id = nation_id
    env.global_strategy = GlobalStrategy.TOTAL_EXPANSIONISM
    env.government_type = GovernmentType.AUTHORITARIAN.value
    env.defense_private_reasoning = "private defense reasoning"
    env.foreign_private_reasoning = "private foreign reasoning"

    # Original proposal (for presidential decisions' action_type)
    env.original_defense_proposal = None

    # Defense payload
    moves = defense_moves or []
    d_payload = MagicMock(spec=DefensePayload)
    d_payload.decision = defense_decision
    d_payload.moves = moves
    env.defense_payload = d_payload

    # Economy payload
    e_payload = MagicMock(spec=EconomicPayload)
    e_payload.action_type = eco_action_type
    e_payload.decision = eco_decision
    e_payload.execution_outcome = eco_outcome or ExecutionOutcome(status="SUCCESS")
    env.economic_payload = e_payload

    # Foreign payload
    f_payload = MagicMock(spec=ForeignPayload)
    f_payload.action_type = for_action_type
    f_payload.decision = for_decision
    f_payload.execution_outcome = for_outcome or ExecutionOutcome(status="SUCCESS")
    env.foreign_payload = f_payload

    return env


def _make_defense_move(
    action_type: DefenseActionType,
    status: str = "SUCCESS",
    reason: str | None = None,
) -> MagicMock:
    """Build a minimal DefenseActionItem mock with execution_outcome."""
    move = MagicMock(spec=DefenseActionItem)
    move.action_type = action_type
    move.execution_outcome = ExecutionOutcome(status=status, reason=reason)
    return move


# ---------------------------------------------------------------------------
# Tests: extract_action_outcomes
# ---------------------------------------------------------------------------

class TestExtractActionOutcomes:
    """Unit tests for extract_action_outcomes()."""

    def test_empty_envelope_yields_economy_and_foreign_only(self):
        """An envelope with no defense moves still produces eco + foreign rows."""
        env = _make_envelope(defense_moves=[])
        rows = extract_action_outcomes(env, turn=3)
        # No defense moves → no defense rows; eco and foreign both have action_type
        domains = [r["domain"] for r in rows]
        assert "Defense" not in domains
        assert "Economy" in domains
        assert "Foreign" in domains

    def test_defense_moves_produce_one_row_each(self):
        """Each move in the defense waterfall generates its own row."""
        moves = [
            _make_defense_move(DefenseActionType.CREATE_UNIT, "SUCCESS"),
            _make_defense_move(DefenseActionType.MOVE_TROOPS, "FAILED", "No path found"),
        ]
        env = _make_envelope(defense_moves=moves)
        rows = extract_action_outcomes(env, turn=5)

        defense_rows = [r for r in rows if r["domain"] == "Defense"]
        assert len(defense_rows) == 2

        statuses = {r["action_type"]: r["status"] for r in defense_rows}
        assert statuses["CREATE_UNIT"] == "SUCCESS"
        assert statuses["MOVE_TROOPS"] == "FAILED"

    def test_failed_reason_is_preserved(self):
        """The failure reason string is stored in the row."""
        moves = [_make_defense_move(DefenseActionType.CREATE_UNIT, "FAILED", "Insufficient budget")]
        env = _make_envelope(defense_moves=moves)
        rows = extract_action_outcomes(env, turn=2)
        defense_row = next(r for r in rows if r["domain"] == "Defense")
        assert defense_row["reason"] == "Insufficient budget"

    def test_economy_failed_status_captured(self):
        """Economy FAILED outcome is captured correctly."""
        env = _make_envelope(
            eco_action_type=EconomicActionType.RAISE_WAR_TAX,
            eco_outcome=ExecutionOutcome(status="FAILED", reason="Satisfaction too low"),
        )
        rows = extract_action_outcomes(env, turn=7)
        eco_row = next(r for r in rows if r["domain"] == "Economy")
        assert eco_row["status"] == "FAILED"
        assert eco_row["action_type"] == "RAISE_WAR_TAX"

    def test_all_rows_have_required_keys(self):
        """Every row contains all keys expected by MetricsDB."""
        env = _make_envelope(defense_moves=[_make_defense_move(DefenseActionType.CREATE_UNIT)])
        rows = extract_action_outcomes(env, turn=1)
        required = {"turn", "nation_id", "domain", "action_type", "status"}
        for row in rows:
            assert required.issubset(row.keys()), f"Missing keys in {row}"

    def test_nation_id_set_correctly(self):
        """nation_id in every row matches the envelope sender_id."""
        env = _make_envelope(nation_id="my_nation")
        rows = extract_action_outcomes(env, turn=1)
        for row in rows:
            assert row["nation_id"] == "my_nation"


# ---------------------------------------------------------------------------
# Tests: extract_presidential_decisions
# ---------------------------------------------------------------------------

class TestExtractPresidentialDecisions:
    """Unit tests for extract_presidential_decisions()."""

    def test_three_domains_always_present(self):
        """One row per domain (Defense, Economy, Foreign) is always produced."""
        env = _make_envelope()
        rows = extract_presidential_decisions(env, turn=1)
        domains = {r["domain"] for r in rows}
        assert domains == {"Defense", "Economy", "Foreign"}

    def test_approve_decision_recorded(self):
        """APPROVE decisions are recorded correctly."""
        env = _make_envelope(
            defense_decision=Decision.APPROVE,
            eco_decision=Decision.APPROVE,
            for_decision=Decision.APPROVE,
        )
        rows = extract_presidential_decisions(env, turn=2)
        for row in rows:
            assert row["decision"] == "APPROVE"

    def test_veto_decision_recorded(self):
        """VETO decisions are recorded correctly for each domain."""
        env = _make_envelope(
            defense_decision=Decision.VETO,
            eco_decision=Decision.VETO,
            for_decision=Decision.VETO,
        )
        rows = extract_presidential_decisions(env, turn=4)
        for row in rows:
            assert row["decision"] == "VETO"

    def test_economy_action_type_in_row(self):
        """The proposed economy action type is stored in the row."""
        env = _make_envelope(eco_action_type=EconomicActionType.TRADE_PROPOSAL)
        rows = extract_presidential_decisions(env, turn=1)
        eco_row = next(r for r in rows if r["domain"] == "Economy")
        assert eco_row["action_type"] == "TRADE_PROPOSAL"

    def test_foreign_reasoning_in_row(self):
        """President's private reasoning for foreign domain is stored."""
        env = _make_envelope(for_decision=Decision.APPROVE)
        rows = extract_presidential_decisions(env, turn=1)
        for_row = next(r for r in rows if r["domain"] == "Foreign")
        assert for_row["reasoning"] == "private foreign reasoning"

    def test_all_rows_have_required_keys(self):
        """Every row contains the keys required by MetricsDB."""
        env = _make_envelope()
        rows = extract_presidential_decisions(env, turn=1)
        required = {"turn", "nation_id", "domain", "decision"}
        for row in rows:
            assert required.issubset(row.keys())


# ---------------------------------------------------------------------------
# Tests: MetricsDB persistence
# ---------------------------------------------------------------------------

class TestMetricsDBPersistence:
    """Integration tests: data flows from extractors into MetricsDB correctly."""

    @pytest.fixture
    def db(self, tmp_path):
        """Provide an isolated in-memory MetricsDB per test."""
        db_path = str(tmp_path / "test_metrics.duckdb")
        m = MetricsDB(db_path)
        yield m
        m.close()

    def test_insert_action_outcomes_persists_rows(self, db):
        """Rows inserted via insert_action_outcomes() are queryable."""
        rows = [
            {
                "turn": 1, "nation_id": "na", "domain": "Defense",
                "action_type": "CREATE_UNIT", "status": "SUCCESS", "reason": None,
            },
            {
                "turn": 1, "nation_id": "na", "domain": "Economy",
                "action_type": "INVEST_WELFARE", "status": "FAILED", "reason": "No budget",
            },
        ]
        db.insert_action_outcomes("sim_1", rows)
        result = db.conn.execute(
            "SELECT * FROM metrics_action_outcomes WHERE simulation_id = 'sim_1'"
        ).fetchall()
        assert len(result) == 2

    def test_insert_presidential_decisions_persists_rows(self, db):
        """Rows inserted via insert_presidential_decisions() are queryable."""
        rows = [
            {
                "turn": 1, "nation_id": "na", "domain": "Defense",
                "decision": "APPROVE", "action_type": "CREATE_UNIT", "reasoning": "looks good",
            },
            {
                "turn": 1, "nation_id": "na", "domain": "Foreign",
                "decision": "VETO", "action_type": "FORMAL_DECLARATION_OF_WAR",
                "reasoning": "too risky",
            },
        ]
        db.insert_presidential_decisions("sim_2", rows)
        result = db.conn.execute(
            "SELECT decision FROM metrics_presidential_decisions WHERE simulation_id = 'sim_2'"
        ).fetchall()
        decisions = {r[0] for r in result}
        assert "APPROVE" in decisions
        assert "VETO" in decisions

    def test_end_to_end_extractor_to_db(self, db):
        """Full pipeline: envelope → extractor → DB → query."""
        moves = [
            _make_defense_move(DefenseActionType.CREATE_UNIT, "SUCCESS"),
            _make_defense_move(DefenseActionType.MOVE_TROOPS, "FAILED", "No path"),
        ]
        env = _make_envelope(nation_id="nation_x", defense_moves=moves)

        outcome_rows = extract_action_outcomes(env, turn=10)
        decision_rows = extract_presidential_decisions(env, turn=10)

        db.insert_action_outcomes("sim_3", outcome_rows)
        db.insert_presidential_decisions("sim_3", decision_rows)

        # Verify action outcomes
        outcome_count = db.conn.execute(
            "SELECT COUNT(*) FROM metrics_action_outcomes WHERE simulation_id='sim_3'"
        ).fetchone()[0]
        assert outcome_count == len(outcome_rows)

        # Verify presidential decisions
        decision_count = db.conn.execute(
            "SELECT COUNT(*) FROM metrics_presidential_decisions WHERE simulation_id='sim_3'"
        ).fetchone()[0]
        assert decision_count == len(decision_rows)
