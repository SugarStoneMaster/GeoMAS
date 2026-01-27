"""
Action Engine.

The orchestrator that coordinates validation and execution of agent actions.
Delegates specific logic to specialized handlers.
"""

from typing import List, Tuple
from geomas.schemas.world import WorldState
from geomas.world.spatial import SpatialManager

from geomas.actions.validators import ActionValidators
from geomas.actions.defense import DefenseActionType, execute_defense_waterfall
from geomas.actions.economy import execute_economic, EconomicActionType
from geomas.actions.foreign import execute_foreign, ForeignActionType


# Constants from economy handler
WAR_TAX_SATISFACTION_PENALTY = 0.15
WAR_TAX_BUDGET_BOOST_RATIO = 0.10


class ActionEngine:
    """
    The Deterministic Rules Oracle & Executor.
    Validates AND executes actions, modifying the WorldState.
    """
    
    # Expose constants for external access if needed
    MIN_SATISFACTION_FOR_WAR_TAX = ActionValidators.MIN_SATISFACTION_FOR_WAR_TAX
    WAR_TAX_SATISFACTION_PENALTY = WAR_TAX_SATISFACTION_PENALTY
    WAR_TAX_BUDGET_BOOST_RATIO = WAR_TAX_BUDGET_BOOST_RATIO


    def __init__(self, world: WorldState):
        self.world = world
        self.spatial = SpatialManager(world)
        self.logs: List[str] = []

    # --- VALIDATION DELEGATION ---

    def can_move_troops(self, nation_id: str, from_prov_id: int, to_prov_id: int) -> Tuple[bool, str]:
        return ActionValidators.can_move_troops(self.world, self.spatial, nation_id, from_prov_id, to_prov_id)

    def can_attack(self, attacker_id: str, target_prov_id: int) -> Tuple[bool, str]:
        return ActionValidators.can_attack(self.world, attacker_id, target_prov_id)

    def can_afford_budget(self, nation_id: str, amount: float) -> Tuple[bool, str]:
        return ActionValidators.can_afford_budget(self.world, nation_id, amount)

    def can_raise_war_tax(self, nation_id: str) -> Tuple[bool, str]:
        return ActionValidators.can_raise_war_tax(self.world, nation_id)

    def can_trade(self, nation_a_id: str, nation_b_id: str) -> Tuple[bool, str]:
        trust = self.world.trust_matrix.get(nation_a_id, {}).get(nation_b_id, 0.5)
        if trust < 0.2: 
            return False, "Relations too hostile for trade."
        return True, "Trade possible."

    # --- EXECUTION DELEGATION ---

    def execute_envelope(self, envelope) -> List[str]:
        """
        Executes all payloads in the envelope.
        Returns a list of execution logs.
        """
        self.logs = []
        sender_id = envelope.sender_id
        
        # 1. Defense (Waterfall)
        execute_defense_waterfall(self, sender_id, envelope.defense_payload)
        
        # 2. Economy
        execute_economic(self, sender_id, envelope.economic_payload)
        
        # 3. Foreign
        execute_foreign(self, sender_id, envelope.foreign_payload)
        
        return self.logs

    def deduct_budget(self, nation_id: str, amount: float):
        """Deduct from nation's total budget."""
        nation = self.world.nations.get(nation_id)
        if nation:
            nation.total_budget -= amount

    def adjust_trust(self, nation_a: str, nation_b: str, delta: float):
        """Adjust trust between two nations."""
        if nation_a not in self.world.trust_matrix:
            self.world.trust_matrix[nation_a] = {}
        
        current = self.world.trust_matrix[nation_a].get(nation_b, 0.5)
        new_trust = max(0.0, min(1.0, current + delta))
        self.world.trust_matrix[nation_a][nation_b] = new_trust
