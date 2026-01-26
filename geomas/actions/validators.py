"""
Action Validators.

Pure functions to check if specific actions are permissible in the current world state.
"""

from typing import Tuple
from geomas.schemas.world import WorldState
from geomas.world.spatial import SpatialManager
import networkx as nx


class ActionValidators:
    """Namespace for validation logic to keep it organized."""
    
    # Constants
    MIN_SATISFACTION_FOR_WAR_TAX = 0.20

    @staticmethod
    def can_move_troops(
        world: WorldState, 
        spatial: SpatialManager, 
        nation_id: str, 
        from_prov_id: int, 
        to_prov_id: int
    ) -> Tuple[bool, str]:
        start_prov = world.provinces.get(from_prov_id)
        if not start_prov or start_prov.owner_id != nation_id:
            return False, f"Province {from_prov_id} does not belong to {nation_id}."

        end_prov = world.provinces.get(to_prov_id)
        if not end_prov:
            return False, "Destination province does not exist."
        
        if end_prov.owner_id != nation_id:
            return False, "Cannot redeploy to foreign territory. Use ATTACK action instead."

        nation_provinces = world.nations[nation_id].province_ids
        subgraph = spatial.graph.subgraph(nation_provinces)
        
        if nx.has_path(subgraph, from_prov_id, to_prov_id):
            return True, "Path clear."
        else:
            return False, "No contiguous path through friendly territory."

    @staticmethod
    def can_attack(
        world: WorldState, 
        attacker_id: str, 
        target_prov_id: int
    ) -> Tuple[bool, str]:
        target_prov = world.provinces.get(target_prov_id)
        if not target_prov: return False, "Target invalid."
        if target_prov.owner_id == attacker_id: return False, "Cannot attack own territory."

        is_neighbor = False
        for neighbor_id in target_prov.neighbors:
            neighbor = world.provinces.get(neighbor_id)
            if neighbor and neighbor.owner_id == attacker_id:
                is_neighbor = True
                break
        
        if is_neighbor: return True, "Valid attack target."
        else: return False, "Target is not adjacent to any owned province."

    @staticmethod
    def can_afford_budget(
        world: WorldState, 
        nation_id: str, 
        amount: float
    ) -> Tuple[bool, str]:
        nation = world.nations.get(nation_id)
        if not nation: return False, "Nation not found."
        
        if nation.total_budget >= amount:
            return True, "Funds available."
        else:
            return False, f"Insufficient funds. Required: {amount}, Available: {nation.total_budget}"

    @staticmethod
    def can_raise_war_tax(world: WorldState, nation_id: str) -> Tuple[bool, str]:
        """Check if nation can raise war tax (satisfaction threshold)."""
        nation = world.nations.get(nation_id)
        if not nation: return False, "Nation not found."
        
        if nation.public_satisfaction >= ActionValidators.MIN_SATISFACTION_FOR_WAR_TAX:
            return True, "Satisfaction sufficient for war tax."
        else:
            return False, f"Satisfaction too low ({nation.public_satisfaction:.2f} < {ActionValidators.MIN_SATISFACTION_FOR_WAR_TAX})"
