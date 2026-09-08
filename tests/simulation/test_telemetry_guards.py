import pytest
import os
from geomas.simulation.engine import SimulationEngine
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy
from geomas.agents.schemas.protocol import GovernmentType
from geomas.actions.defense.schemas import DefensePayload, Decision
from geomas.actions.defense.handler import DefensePayload
from geomas.actions.common import Decision

def test_telemetry_guards_for_inactive_nations(tmp_path):
    # 1. Setup engine with persistence
    db_path = str(tmp_path / "test_metrics.duckdb")
    engine = SimulationEngine(map_seed=42, n_cells=100, db_path=db_path)
    
    # Ensure we have at least 2 nations
    nation_ids = sorted(list(engine.world.nations.keys()))
    active_id = nation_ids[0]
    inactive_id = nation_ids[1]
    
    active_nation = engine.world.nations[active_id]
    inactive_nation = engine.world.nations[inactive_id]
    
    # 2. Mark one nation as inactive
    inactive_nation.is_active = False
    inactive_nation.province_ids = [] # Standard elimination state
    
    from geomas.agents.schemas.protocol import DefenseIntentType, ForeignIntentType
    from geomas.actions.economy import EconomicPayload
    from geomas.actions.foreign import ForeignPayload

    # 3. Create envelopes for both
    # Even if the inactive nation somehow produces an envelope (e.g. mock or lag)
    envelope_active = CountryEnvelope(
        turn=1,
        sender_id=active_id,
        global_strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
        government_type=GovernmentType.DEMOCRACY.value,
        public_statement="Active",
        defense_payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
        defense_public_intent=DefenseIntentType.IDLE,
        defense_private_intent=DefenseIntentType.IDLE,
        defense_private_reasoning="None",
        economic_payload=EconomicPayload(decision=Decision.APPROVE, action_type=None),
        economic_private_reasoning="None",
        foreign_payload=ForeignPayload(decision=Decision.APPROVE, action_type=None),
        foreign_public_intent=ForeignIntentType.IDLE,
        foreign_private_intent=ForeignIntentType.IDLE,
        foreign_private_reasoning="None"
    )
    
    envelope_inactive = CountryEnvelope(
        turn=1,
        sender_id=inactive_id,
        global_strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
        government_type=GovernmentType.DEMOCRACY.value,
        public_statement="Ghost",
        defense_payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
        defense_public_intent=DefenseIntentType.IDLE,
        defense_private_intent=DefenseIntentType.IDLE,
        defense_private_reasoning="None",
        economic_payload=EconomicPayload(decision=Decision.APPROVE, action_type=None),
        economic_private_reasoning="None",
        foreign_payload=ForeignPayload(decision=Decision.APPROVE, action_type=None),
        foreign_public_intent=ForeignIntentType.IDLE,
        foreign_private_intent=ForeignIntentType.IDLE,
        foreign_private_reasoning="None"
    )
    
    envelopes = [envelope_active, envelope_inactive]
    
    # 4. Trigger persistence
    engine._persist_envelopes(turn=1, envelopes=envelopes)
    
    # 5. Verify MetricsDB content
    # Inactive nation should have NO entries in metrics_nation
    metrics_conn = engine.metrics_db.conn
    
    # Check Nation Metrics
    nation_results = metrics_conn.execute(
        "SELECT nation_id FROM metrics_nation WHERE turn = 1"
    ).fetchall()
    
    nation_ids_logged = [r[0] for r in nation_results]
    assert active_id in nation_ids_logged
    assert inactive_id not in nation_ids_logged
    
    # Check Trust Metrics
    trust_results = metrics_conn.execute(
        "SELECT observer_id, target_id FROM metrics_trust WHERE turn = 1"
    ).fetchall()
    
    for obs_id, target_id in trust_results:
        assert obs_id != inactive_id
        assert target_id != inactive_id

if __name__ == "__main__":
    pytest.main([__file__])
