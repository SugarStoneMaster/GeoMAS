"""
Territory Management Module.

Handles dynamic updates to province ownership and classification,
specifically territorial waters.
"""

from typing import TYPE_CHECKING
from geomas.schemas.world import TerrainType

if TYPE_CHECKING:
    from geomas.schemas.world import WorldState


def update_territorial_waters(world: 'WorldState', coastal_province_id: int) -> None:
    """
    Updates ownership of adjacent ocean provinces based on coastal ownership.
    
    Rule: An Ocean province is a Territorial Water of Nation X if ALL
    its land/coastal neighbors are owned by Nation X.
    If it has neighbors from multiple nations, or no owner, it is International Waters (neutral).
    
    Args:
        world: The world state.
        coastal_province_id: The ID of the coastal province that changed owner.
    """
    coastal_prov = world.provinces.get(coastal_province_id)
    if not coastal_prov or coastal_prov.terrain not in (TerrainType.COASTAL, TerrainType.LAND):
        return

    # Check all adjacent OCEAN provinces
    for neighbor_id in coastal_prov.neighbors:
        ocean_prov = world.provinces.get(neighbor_id)
        if not ocean_prov or ocean_prov.terrain != TerrainType.OCEAN:
            continue
            
        # For this ocean province, check all its neighbors
        adjacent_owners = set()
        has_unowned_neighbor = False
        
        for n_id in ocean_prov.neighbors:
            n_prov = world.provinces.get(n_id)
            if not n_prov:
                continue
            
            # We only care about land/coastal neighbors for ownership determination
            if n_prov.terrain in (TerrainType.COASTAL, TerrainType.LAND, TerrainType.MOUNTAIN):
                if n_prov.owner_id:
                    adjacent_owners.add(n_prov.owner_id)
                else:
                    has_unowned_neighbor = True
        
        # LOGIC:
        # If exactly ONE nation owns all adjacent land, it claims the water.
        # Otherwise (multiple nations or unowned land), it is neutral.
        
        old_owner = ocean_prov.owner_id
        new_owner = None
        
        if len(adjacent_owners) == 1 and not has_unowned_neighbor:
            new_owner = list(adjacent_owners)[0]
        
        # Apply Change
        if old_owner != new_owner:
            # 1. Remove from old owner
            if old_owner:
                old_nation = world.nations.get(old_owner)
                if old_nation and ocean_prov.id in old_nation.territorial_water_ids:
                    old_nation.territorial_water_ids.remove(ocean_prov.id)
            
            # 2. Add to new owner
            if new_owner:
                new_nation = world.nations.get(new_owner)
                if new_nation:
                    new_nation.territorial_water_ids.append(ocean_prov.id)
            
            # 3. Update province
            ocean_prov.owner_id = new_owner
            
            # Log (optional, maybe verbose)
            # print(f"Territorial Water Update: {ocean_prov.id} changed from {old_owner} to {new_owner}")
