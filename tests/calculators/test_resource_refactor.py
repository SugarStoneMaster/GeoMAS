import pytest
from geomas.schemas.world import WorldState, NationState, ProvinceState, TerrainType
from geomas.calculators.production import calculate_nation_production_multiplier
from geomas.calculators.consumption import calculate_budget_upkeep
from geomas.simulation.phases import run_upkeep_phase

def test_unified_production_multiplier():
    """Verify that satisfaction, workforce, and energy stack correctly."""
    # Mock nation with 50% workforce (1.0 mult), 50 satisfaction (1.0 mult), 0 energy deficit (1.0 mult)
    nation = NationState(
        id="TEST", name="Test", color="#000000",
        total_population=1000, total_workers=500, # 50%
        public_satisfaction=50.0
    )
    
    # 1. Base case
    mult = calculate_nation_production_multiplier(nation, energy_deficit=0.0)
    assert mult == 1.0
    
    # 2. Workforce penalty (25% workers = 0.5 mult)
    nation.total_workers = 250
    mult = calculate_nation_production_multiplier(nation, energy_deficit=0.0)
    assert mult == 0.5
    
    # 3. Satisfaction penalty (10 sat = 0.5 mult)
    nation.public_satisfaction = 10.0
    # mult = 0.5 (workforce) * 0.5 (sat) = 0.25
    mult = calculate_nation_production_multiplier(nation, energy_deficit=0.0)
    assert mult == 0.25
    
    # 4. Energy penalty (50 deficit = 0.5 mult)
    # mult = 0.25 * 0.5 = 0.125
    mult = calculate_nation_production_multiplier(nation, energy_deficit=-50.0)
    assert mult == 0.125

def test_budget_upkeep():
    """Verify units cost budget."""
    # 100 soldiers @ 0.2 = 20
    # 10 aircraft @ 5.0 = 50
    # 5 navy @ 4.0 = 20
    # Total = 90
    upkeep = calculate_budget_upkeep(total_soldiers=100, total_aircraft=10, total_navy=5)
    assert upkeep == 90.0

def test_upkeep_phase_non_destructive():
    """Verify that upkeep does not permanently damage province production."""
    world = WorldState()
    nation = NationState(
        id="N1", name="Nation 1", color="#FF0000",
        province_ids=[1], total_energy=-100.0, # Massive deficit
        public_satisfaction=50.0
    )
    province = ProvinceState(
        id=1, owner_id="N1", terrain=TerrainType.LAND, 
        coordinates=(0.0, 0.0), population=100, workers=50,
        food_production=10.0, energy_production=10.0, materials_production=10.0
    )
    world.nations["N1"] = nation
    world.provinces[1] = province
    
    logs = []
    # Turn 1: Energy deficit causes penalty
    run_upkeep_phase(world, logs)
    
    # Production should have been penalized but province values should be UNCHANGED
    assert province.food_production == 10.0
    # Multiplier should have been 0.5 (max energy penalty)
    # total_food = initial(0) + 10*0.5 - 100(pop) = -95 (clamped to 0 at end)
    # Wait, nation.total_food was 0, consumed 100, added 5. Result -95.
    
    # Turn 2: Give energy
    nation.total_energy = 1000.0
    run_upkeep_phase(world, logs)
    
    # Production should be 100% again because multiplier is 1.0 and province was not destroyed
    # total_food = 0 (prev turn end) + 10*1.0 - 100 = -90
    # The key is that food_production is still 10.0
    assert province.food_production == 10.0
