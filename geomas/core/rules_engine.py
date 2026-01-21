from typing import Tuple, Optional, List, Dict, Any
from geomas.schemas.world import WorldState, ResourceBundle
from geomas.schemas.actions import ActionType, MilitaryPayload, EconomicPayload, ForeignPayload
from geomas.world.spatial_manager import SpatialManager

class ActionEngine:
    """
    The Deterministic Rules Oracle & Executor.
    Validates AND executes actions, modifying the WorldState.
    """

    # --- COST CONFIGURATION ---
    COSTS = {
        ActionType.CREATE_UNIT: 100.0,
        ActionType.MOVE_TROOPS: 20.0,
        ActionType.INVEST_WELFARE: 100.0,
        ActionType.SEND_DIPLOMATIC_MESSAGE: 0.0,
        ActionType.IMPOSE_SANCTIONS: 10.0, # Administrative cost
    }

    def __init__(self, world: WorldState):
        self.world = world
        self.spatial = SpatialManager(world)
        self.logs: List[str] = []

    # --- VALIDATION (Read-Only) ---

    def can_move_troops(self, nation_id: str, from_prov_id: int, to_prov_id: int) -> Tuple[bool, str]:
        start_prov = self.world.provinces.get(from_prov_id)
        if not start_prov or start_prov.owner_id != nation_id:
            return False, f"Province {from_prov_id} does not belong to {nation_id}."

        end_prov = self.world.provinces.get(to_prov_id)
        if not end_prov:
            return False, "Destination province does not exist."
        
        if end_prov.owner_id != nation_id:
            return False, "Cannot redeploy to foreign territory. Use ATTACK action instead."

        nation_provinces = self.world.nations[nation_id].province_ids
        subgraph = self.spatial.graph.subgraph(nation_provinces)
        
        import networkx as nx
        if nx.has_path(subgraph, from_prov_id, to_prov_id):
            return True, "Path clear."
        else:
            return False, "No contiguous path through friendly territory."

    def can_attack(self, attacker_id: str, target_prov_id: int) -> Tuple[bool, str]:
        target_prov = self.world.provinces.get(target_prov_id)
        if not target_prov: return False, "Target invalid."
        if target_prov.owner_id == attacker_id: return False, "Cannot attack own territory."

        is_neighbor = False
        for neighbor_id in target_prov.neighbors:
            neighbor = self.world.provinces.get(neighbor_id)
            if neighbor and neighbor.owner_id == attacker_id:
                is_neighbor = True
                break
        
        if is_neighbor: return True, "Valid attack target."
        else: return False, "Target is not adjacent to any owned province."

    def can_afford_budget(self, nation_id: str, amount: float) -> Tuple[bool, str]:
        nation = self.world.nations.get(nation_id)
        if not nation: return False, "Nation not found."
        
        if nation.internal_state.budget >= amount:
            return True, "Funds available."
        else:
            return False, f"Insufficient funds. Required: {amount}, Available: {nation.internal_state.budget}"

    def can_trade(self, nation_a_id: str, nation_b_id: str) -> Tuple[bool, str]:
        trust = self.world.trust_matrix.get(nation_a_id, {}).get(nation_b_id, 0.5)
        if trust < 0.2: return False, "Relations too hostile for trade."
        return True, "Trade possible."

    # --- EXECUTION (State Modification) ---

    def execute_envelope(self, envelope) -> List[str]:
        """
        Executes all payloads in the envelope.
        Returns a list of execution logs.
        """
        self.logs = []
        sender_id = envelope.sender_id
        
        # 1. Military (Waterfall)
        self._execute_military_waterfall(sender_id, envelope.military_payload)
        
        # 2. Economic
        self._execute_economic(sender_id, envelope.economic_payload)
        
        # 3. Foreign
        self._execute_foreign(sender_id, envelope.foreign_payload)
        
        return self.logs

    def _execute_military_waterfall(self, nation_id: str, payload: MilitaryPayload):
        # Sort by priority (1 is highest)
        moves = sorted(payload.moves, key=lambda x: x.priority)
        
        for move in moves:
            cost = self.COSTS.get(move.action_type, 0.0)
            
            # Check Budget
            allowed, reason = self.can_afford_budget(nation_id, cost)
            if not allowed:
                self.logs.append(f"[MILITARY] Skipped {move.action_type}: {reason}")
                continue # Skip this move, try next (Waterfall)
            
            # Execute
            if move.action_type == ActionType.MOBILIZE_UNIT:
                self._deduct_budget(nation_id, cost)
                self.world.nations[nation_id].internal_state.military_readiness += 0.05
                self.logs.append(f"[MILITARY] Mobilized unit. Readiness +0.05. Cost: {cost}")
                
            elif move.action_type == ActionType.FORTIFY_PROVINCE:
                # Logic to add defense bonus to province
                self._deduct_budget(nation_id, cost)
                self.logs.append(f"[MILITARY] Fortified province. Cost: {cost}")
                
            # Add other military actions...

    def _execute_economic(self, nation_id: str, payload: EconomicPayload):
        if not payload.action_type: return
        
        cost = self.COSTS.get(payload.action_type, 0.0)
        # Dynamic cost for Welfare (based on parameter)
        if payload.action_type == ActionType.INVEST_WELFARE:
            cost = payload.parameters.get("amount", 100.0)
            
        allowed, reason = self.can_afford_budget(nation_id, cost)
        if not allowed:
            self.logs.append(f"[ECONOMIC] Failed {payload.action_type}: {reason}")
            return

        if payload.action_type == ActionType.INVEST_WELFARE:
            self._deduct_budget(nation_id, cost)
            self.world.nations[nation_id].internal_state.public_satisfaction += 0.05
            self.logs.append(f"[ECONOMIC] Invested {cost} in Welfare. Satisfaction +0.05")

    def _execute_foreign(self, nation_id: str, payload: ForeignPayload):
        if not payload.action_type: return
        
        # Foreign actions usually cheap or free, but check constraints
        if payload.action_type == ActionType.SEND_DIPLOMATIC_MESSAGE:
            target = payload.target_nation_id
            msg = payload.parameters.get("message", "")
            self.logs.append(f"[DIPLOMACY] Message to {target}: '{msg}'")
            
            # Effect: Small trust boost if friendly?
            # For now just log.

    def _deduct_budget(self, nation_id: str, amount: float):
        self.world.nations[nation_id].internal_state.budget -= amount
