import math
from typing import Tuple, Optional, List, Dict, Any

from geomas.schemas.world import WorldState
from geomas.schemas.actions import ActionType, MilitaryPayload, EconomicPayload, ForeignPayload
from geomas.world.spatial_manager import SpatialManager
from geomas.core.trade_oracle import TradeOffer, evaluate_trade


class ActionEngine:
    """
    The Deterministic Rules Oracle & Executor.
    Validates AND executes actions, modifying the WorldState.
    """

    # --- COST CONFIGURATION ---
    COSTS = {
        ActionType.CREATE_UNIT: 100.0,
        ActionType.MOVE_TROOPS: 20.0,
        ActionType.INVEST_WELFARE: 100.0,  # Base cost, can be overridden
        ActionType.SEND_DIPLOMATIC_MESSAGE: 0.0,
        ActionType.TRADE_PROPOSAL: 10.0,  # Administrative cost
        ActionType.RAISE_WAR_TAX: 0.0,  # No budget cost, but satisfaction cost
    }
    
    # --- THRESHOLDS ---
    MIN_SATISFACTION_FOR_WAR_TAX = 0.20
    WAR_TAX_SATISFACTION_PENALTY = 0.15
    WAR_TAX_BUDGET_BOOST_RATIO = 0.10  # 10% of total population as budget

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
        
        # Use total_budget (new field) instead of internal_state.budget
        if nation.total_budget >= amount:
            return True, "Funds available."
        else:
            return False, f"Insufficient funds. Required: {amount}, Available: {nation.total_budget}"

    def can_trade(self, nation_a_id: str, nation_b_id: str) -> Tuple[bool, str]:
        trust = self.world.trust_matrix.get(nation_a_id, {}).get(nation_b_id, 0.5)
        if trust < 0.2: return False, "Relations too hostile for trade."
        return True, "Trade possible."
    
    def can_raise_war_tax(self, nation_id: str) -> Tuple[bool, str]:
        """Check if nation can raise war tax (satisfaction threshold)."""
        nation = self.world.nations.get(nation_id)
        if not nation: return False, "Nation not found."
        
        if nation.internal_state.public_satisfaction >= self.MIN_SATISFACTION_FOR_WAR_TAX:
            return True, "Satisfaction sufficient for war tax."
        else:
            return False, f"Satisfaction too low ({nation.internal_state.public_satisfaction:.2f} < {self.MIN_SATISFACTION_FOR_WAR_TAX})"

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
                continue
            
            # Execute
            if move.action_type == ActionType.CREATE_UNIT:
                self._deduct_budget(nation_id, cost)
                # TODO: Add actual unit to province in Phase 4
                self.logs.append(f"[MILITARY] Created unit. Cost: {cost}")
                
            # TODO: Add MOVE_TROOPS, NUCLEAR_OPTION in Phase 4

    def _execute_economic(self, nation_id: str, payload: EconomicPayload):
        if not payload.action_type:
            return
        
        nation = self.world.nations.get(nation_id)
        if not nation:
            return
        
        # --- INVEST_WELFARE ---
        if payload.action_type == ActionType.INVEST_WELFARE:
            amount = payload.parameters.get("amount", 100.0)
            
            # Check budget
            allowed, reason = self.can_afford_budget(nation_id, amount)
            if not allowed:
                self.logs.append(f"[ECONOMIC] Failed INVEST_WELFARE: {reason}")
                return
            
            # Deduct budget
            self._deduct_budget(nation_id, amount)
            
            # Diminishing returns: satisfaction += log(amount) * 0.1
            if amount > 0:
                satisfaction_gain = math.log(amount) * 0.02
                nation.internal_state.public_satisfaction = min(
                    1.0,
                    nation.internal_state.public_satisfaction + satisfaction_gain
                )
                self.logs.append(
                    f"[ECONOMIC] Invested {amount:.0f} in Welfare. "
                    f"Satisfaction +{satisfaction_gain:.3f} (now {nation.internal_state.public_satisfaction:.2f})"
                )
        
        # --- RAISE_WAR_TAX ---
        elif payload.action_type == ActionType.RAISE_WAR_TAX:
            allowed, reason = self.can_raise_war_tax(nation_id)
            if not allowed:
                self.logs.append(f"[ECONOMIC] Failed RAISE_WAR_TAX: {reason}")
                return
            
            # Calculate tax boost based on population
            tax_boost = nation.total_population * self.WAR_TAX_BUDGET_BOOST_RATIO
            
            # Apply effects
            nation.total_budget += tax_boost
            nation.internal_state.public_satisfaction -= self.WAR_TAX_SATISFACTION_PENALTY
            nation.internal_state.public_satisfaction = max(0.0, nation.internal_state.public_satisfaction)
            
            self.logs.append(
                f"[ECONOMIC] War Tax raised! Budget +{tax_boost:.0f}, "
                f"Satisfaction -{self.WAR_TAX_SATISFACTION_PENALTY:.2f} (now {nation.internal_state.public_satisfaction:.2f})"
            )
        
        # --- TRADE_PROPOSAL ---
        elif payload.action_type == ActionType.TRADE_PROPOSAL:
            target_id = payload.target_nation_id
            if not target_id:
                self.logs.append("[ECONOMIC] Failed TRADE_PROPOSAL: No target specified")
                return
            
            # Build TradeOffer from parameters
            give = payload.parameters.get("give", {})
            receive = payload.parameters.get("receive", {})
            
            offer = TradeOffer(
                sender_id=nation_id,
                receiver_id=target_id,
                give=give,
                receive=receive
            )
            
            # Evaluate trade using Trade Oracle
            accepted, explanation = evaluate_trade(offer, self.world)
            
            if accepted:
                # Execute trade: transfer resources
                self._execute_trade(offer)
                
                # Boost trust slightly
                self._adjust_trust(nation_id, target_id, 0.02)
                self._adjust_trust(target_id, nation_id, 0.02)
                
                self.logs.append(f"[TRADE] {nation_id} → {target_id}: {explanation}")
            else:
                self.logs.append(f"[TRADE] {nation_id} → {target_id}: {explanation}")

    def _execute_trade(self, offer: TradeOffer):
        """Execute a trade by transferring resources between nations."""
        sender = self.world.nations.get(offer.sender_id)
        receiver = self.world.nations.get(offer.receiver_id)
        
        if not sender or not receiver:
            return
        
        # Sender gives resources to receiver
        for resource, amount in offer.give.items():
            sender_attr = f"total_{resource}"
            receiver_attr = f"total_{resource}"
            
            if hasattr(sender, sender_attr) and hasattr(receiver, receiver_attr):
                current_sender = getattr(sender, sender_attr)
                current_receiver = getattr(receiver, receiver_attr)
                
                # Can't give more than you have
                actual_amount = min(amount, current_sender)
                setattr(sender, sender_attr, current_sender - actual_amount)
                setattr(receiver, receiver_attr, current_receiver + actual_amount)
        
        # Receiver gives resources to sender
        for resource, amount in offer.receive.items():
            receiver_attr = f"total_{resource}"
            sender_attr = f"total_{resource}"
            
            if hasattr(receiver, receiver_attr) and hasattr(sender, sender_attr):
                current_receiver = getattr(receiver, receiver_attr)
                current_sender = getattr(sender, sender_attr)
                
                actual_amount = min(amount, current_receiver)
                setattr(receiver, receiver_attr, current_receiver - actual_amount)
                setattr(sender, sender_attr, current_sender + actual_amount)

    def _adjust_trust(self, nation_a: str, nation_b: str, delta: float):
        """Adjust trust between two nations."""
        if nation_a not in self.world.trust_matrix:
            self.world.trust_matrix[nation_a] = {}
        
        current = self.world.trust_matrix[nation_a].get(nation_b, 0.5)
        new_trust = max(0.0, min(1.0, current + delta))
        self.world.trust_matrix[nation_a][nation_b] = new_trust

    def _execute_foreign(self, nation_id: str, payload: ForeignPayload):
        if not payload.action_type:
            return
        
        if payload.action_type == ActionType.SEND_DIPLOMATIC_MESSAGE:
            target = payload.target_nation_id
            msg = payload.parameters.get("message", "")
            self.logs.append(f"[DIPLOMACY] Message to {target}: '{msg}'")
            
            # Small trust boost for friendly communication
            if target:
                self._adjust_trust(nation_id, target, 0.01)
                self._adjust_trust(target, nation_id, 0.01)

    def _deduct_budget(self, nation_id: str, amount: float):
        """Deduct from nation's total budget."""
        nation = self.world.nations.get(nation_id)
        if nation:
            nation.total_budget -= amount
