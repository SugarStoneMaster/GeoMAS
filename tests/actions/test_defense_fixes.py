"""
Tests for Defense Logic Fixes.

Verifies:
- Negative troop/unit quantity validation (Pydantic)
- Suicide check (Handler)
- Target self validation (Validators/Schema)
"""

import pytest
from pydantic import ValidationError
from geomas.actions.defense.schemas import DefensePayload, DefenseActionItem, DefenseActionType, UnitType
from geomas.actions.common import Decision
from geomas.actions.validators import ActionValidators
from geomas.world import generate_world
from geomas.actions.engine import ActionEngine
from conftest import create_test_envelope
from geomas.schemas.world import TerrainType

class TestDefenseSchemaFixes:
    """Tests for Pydantic schema validation fixes."""
    
    def test_negative_quantity_raises_error(self):
        """Test that negative quantity raises ValidationError."""
        with pytest.raises(ValidationError) as excinfo:
            DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                quantity=-5,
                source_province_id=1,
                target_province_id=2
            )
        assert "greater than 0" in str(excinfo.value)
        
    def test_zero_quantity_raises_error(self):
        """Test that zero quantity raises ValidationError."""
        with pytest.raises(ValidationError):
            DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                quantity=0,
                source_province_id=1,
                target_province_id=2
            )

    def test_missing_source_for_move_raises_error(self):
        """Test that missing source_province_id for MOVE_TROOPS raises error."""
        with pytest.raises(ValidationError) as excinfo:
            # We must use model_validate/validator to trigger the check if it's a model validator
            # But here it is a field validator on source_province_id which runs on assignment/init
            # However, if the field is Optional, it might need explicit validation or 
            # the validator needs to run 'always'. 
            # Let's try constructing and then validating if pydantic V2.
            
            DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                target_province_id=2,
                source_province_id=None # Explicitly None to trigger validator
            )
        assert "source_province_id is required" in str(excinfo.value)


class TestDefenseLogicFixes:
    """Tests for handler logic fixes."""
    
    def test_suicide_check_aborts_attack(self):
        """Test that attacking with <10% of defenders forces aborts."""
        world = generate_world(seed=42, n_cells=50, n_nations=2)
        engine = ActionEngine(world)
        nations = list(world.nations.values())
        attacker_n = nations[0]
        defender_n = nations[1]
        
        attacker_id = attacker_n.id
        defender_id = defender_n.id
        
        # Setup: Attacker has 10 soldiers, Defender has 200 soldiers
        # Threshold: 200 * 0.1 = 20. Attacking with 10 should fail.
        
        # Find adjacent provinces
        start_prov_id = attacker_n.province_ids[0]
        target_prov_id = defender_n.province_ids[0]
        
        # Hack geometry to make them neighbors and LAND
        start_prov = world.provinces[start_prov_id]
        target_prov = world.provinces[target_prov_id]
        
        # Ensure adjacency in graph
        start_prov.neighbors.append(target_prov_id)
        target_prov.neighbors.append(start_prov_id)
        engine.spatial.graph.add_edge(start_prov_id, target_prov_id)
        
        start_prov.terrain = TerrainType.LAND
        target_prov.terrain = TerrainType.LAND
        
        start_prov.soldiers = 100
        target_prov.soldiers = 200 # Strong defense
        
        # Action: Move 10 soldiers
        payload = DefensePayload(
            decision=Decision.APPROVE,
            moves=[DefenseActionItem(
                priority=1,
                action_type=DefenseActionType.MOVE_TROOPS,
                unit_type=UnitType.SOLDIER,
                quantity=10,
                source_province_id=start_prov_id,
                target_province_id=target_prov_id,
                target_nation_id=defender_id
            )]
        )
        
        envelope = create_test_envelope(attacker_id, defense_payload=payload)
        logs = engine.execute_envelope(envelope)
        
        # Verify abortion
        assert any("Suicide attack aborted" in log for log in logs)
        assert start_prov.soldiers == 100 # No change (refunded)
        assert target_prov.soldiers == 200 # No damage

    def test_validate_target_is_not_self(self):
        """Test the validator directly."""
        valid, msg = ActionValidators.validate_target_is_not_self("A", "B", "ATTACK")
        assert valid is True
        
        valid, msg = ActionValidators.validate_target_is_not_self("A", "A", "ATTACK")
        assert valid is False
        assert "cannot target self" in msg
