from typing import Tuple, Optional
from geomas.schemas.models import WorldState, ResourceBundle
from geomas.world.spatial_manager import SpatialManager

class ActionValidator:
    """
    The Deterministic Rules Oracle.
    Validates actions against physical, economic, and diplomatic constraints.
    Returns (bool, reason) tuples for Explainability.
    """

    def __init__(self, world: WorldState):
        self.world = world
        self.spatial = SpatialManager(world)

    # --- SPATIAL RULES ---

    def can_move_troops(self, nation_id: str, from_prov_id: int, to_prov_id: int) -> Tuple[bool, str]:
        """
        Checks if troops can move between two provinces.
        Rule: Must be a valid path through owned territory or allied territory (Military Access).
        For Phase 1, we simplify: Path must be through OWNED territory only.
        """
        # 1. Ownership Check
        start_prov = self.world.provinces.get(from_prov_id)
        if not start_prov or start_prov.owner_id != nation_id:
            return False, f"Province {from_prov_id} does not belong to {nation_id}."

        # 2. Destination Check (Can only move to own territory or attack neighbor)
        # For simple movement (redeployment), dest must be owned.
        end_prov = self.world.provinces.get(to_prov_id)
        if not end_prov:
            return False, "Destination province does not exist."
        
        if end_prov.owner_id != nation_id:
            return False, "Cannot redeploy to foreign territory. Use ATTACK action instead."

        # 3. Pathfinding Check (Contiguity)
        # We need to check if a path exists strictly within the nation's own territory.
        # We create a temporary subgraph of the nation's provinces.
        nation_provinces = self.world.nations[nation_id].province_ids
        subgraph = self.spatial.graph.subgraph(nation_provinces)
        
        import networkx as nx
        if nx.has_path(subgraph, from_prov_id, to_prov_id):
            return True, "Path clear."
        else:
            return False, "No contiguous path through friendly territory."

    def can_attack(self, attacker_id: str, target_prov_id: int) -> Tuple[bool, str]:
        """
        Checks if a nation can launch an attack on a target province.
        Rule: Target must be a neighbor of at least one owned province.
        """
        target_prov = self.world.provinces.get(target_prov_id)
        if not target_prov:
            return False, "Target invalid."
        
        if target_prov.owner_id == attacker_id:
            return False, "Cannot attack own territory."

        # Check adjacency
        is_neighbor = False
        for neighbor_id in target_prov.neighbors:
            neighbor = self.world.provinces.get(neighbor_id)
            if neighbor and neighbor.owner_id == attacker_id:
                is_neighbor = True
                break
        
        if is_neighbor:
            return True, "Valid attack target."
        else:
            return False, "Target is not adjacent to any owned province."

    # --- ECONOMIC RULES ---

    def can_afford(self, nation_id: str, cost: ResourceBundle) -> Tuple[bool, str]:
        """
        Checks if the nation has enough resources.
        Note: Currently resources are stored in provinces, but budget is in MinisterialState.
        We need to decide if 'cost' is budget (money) or raw resources.
        For now, let's assume 'cost' refers to the Ministerial Budget for simplicity,
        or we aggregate province resources.
        
        Let's implement a Budget check first.
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return False, "Nation not found."

        # Check Budget (Money)
        # Assuming cost.energy is actually money for this specific function signature,
        # OR we need to define what 'cost' means.
        # Let's assume we are checking the 'budget' field in MinisterialState.
        # We'll overload this: if cost is a float, it's budget.
        
        # TODO: Refactor this when we have a clear 'Cost' object.
        # For now, let's implement a simple budget check.
        return True, "Not implemented yet."

    def can_afford_budget(self, nation_id: str, amount: float) -> Tuple[bool, str]:
        nation = self.world.nations.get(nation_id)
        if not nation: return False, "Nation not found."
        
        if nation.internal_state.budget >= amount:
            return True, "Funds available."
        else:
            return False, f"Insufficient funds. Required: {amount}, Available: {nation.internal_state.budget}"

    # --- DIPLOMATIC RULES ---

    def can_trade(self, nation_a_id: str, nation_b_id: str) -> Tuple[bool, str]:
        """
        Checks if trade is possible.
        Rule: Must not be at war (Trust > 0.1 is a placeholder proxy).
        """
        trust = self.world.trust_matrix.get(nation_a_id, {}).get(nation_b_id, 0.5)
        
        if trust < 0.2:
            return False, "Relations too hostile for trade."
        
        return True, "Trade possible."
