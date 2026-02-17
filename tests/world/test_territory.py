
import pytest
from geomas.schemas.world import WorldState, ProvinceState, NationState, TerrainType
from geomas.world.territory import update_territorial_waters
from geomas.actions.defense.combat import _conquer_province

@pytest.fixture
def mock_world():
    """
    Setup a mini-world with:
    - 1 Ocean province (ID 0)
    - 2 Coastal provinces (ID 1, 2) bordering the ocean
    - 2 Nations (N1, N2) owning one coastal province each
    """
    world = WorldState()
    
    # Create Nations
    world.nations["N1"] = NationState(id="N1", name="Nation 1", color="#FF0000")
    world.nations["N2"] = NationState(id="N2", name="Nation 2", color="#0000FF")
    
    # Create Provinces
    # P0 = Ocean (Initially Neutral)
    p0 = ProvinceState(
        id=0, owner_id=None, terrain=TerrainType.OCEAN, 
        coordinates=(0,0), neighbors=[1, 2]
    )
    
    # P1 = Costal (Owned by N1)
    p1 = ProvinceState(
        id=1, owner_id="N1", terrain=TerrainType.COASTAL, 
        coordinates=(1,0), neighbors=[0]
    )
    world.nations["N1"].province_ids.append(1)
    
    # P2 = Coastal (Owned by N2)
    p2 = ProvinceState(
        id=2, owner_id="N2", terrain=TerrainType.COASTAL, 
        coordinates=(-1,0), neighbors=[0]
    )
    world.nations["N2"].province_ids.append(2)
    
    world.provinces = {0: p0, 1: p1, 2: p2}
    
    return world

def test_initial_neutrality(mock_world):
    """
    Scenario: N1 owns P1, N2 owns P2. Both border Ocean P0.
    Expectation: P0 is Neutral (International Waters) because neighbors are split.
    """
    # Run update on P1 to simulate initial check
    update_territorial_waters(mock_world, 1)
    
    p0 = mock_world.provinces[0]
    assert p0.owner_id is None
    assert 0 not in mock_world.nations["N1"].territorial_water_ids
    assert 0 not in mock_world.nations["N2"].territorial_water_ids

def test_conquest_unifies_waters(mock_world):
    """
    Scenario: N1 conquers P2. Now N1 owns ALL land neighbors of P0.
    Expectation: P0 becomes Territorial Waters of N1.
    """
    p2 = mock_world.provinces[2]
    
    # N1 conquers P2
    # We use _conquer_province to test the integration hook
    _conquer_province(mock_world, "N1", p2)
    
    # Verify P2 ownership change
    assert p2.owner_id == "N1"
    assert 2 in mock_world.nations["N1"].province_ids
    assert 2 not in mock_world.nations["N2"].province_ids
    
    # Manually trigger update if _conquer_province didn't (it should have if updated)
    # But wait, we modified _conquer_province to call it. 
    # Let's verify AUTOMATIC update first.
    
    p0 = mock_world.provinces[0]
    assert p0.owner_id == "N1", "Ocean P0 should now be owned by N1"
    assert 0 in mock_world.nations["N1"].territorial_water_ids

def test_loss_reverts_to_neutral(mock_world):
    """
    Scenario: N1 owns everything. Then N2 conquers P2 back.
    Expectation: P0 reverts to Neutral (International Waters).
    """
    # 1. Setup N1 dominance first
    p2 = mock_world.provinces[2]
    _conquer_province(mock_world, "N1", p2)
    
    p0 = mock_world.provinces[0]
    assert p0.owner_id == "N1" # Pre-condition
    
    # 2. N2 re-conquers P2
    _conquer_province(mock_world, "N2", p2)
    
    # Verify P2 is N2
    assert p2.owner_id == "N2"
    
    # Verify Oceanic Neutrality
    assert p0.owner_id is None, "Ocean P0 should revert to Neutral"
    assert 0 not in mock_world.nations["N1"].territorial_water_ids
    assert 0 not in mock_world.nations["N2"].territorial_water_ids
