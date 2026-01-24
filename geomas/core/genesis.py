import numpy as np
from typing import List, Dict, Tuple, Any
from geomas.schemas.world import WorldState, TerrainType # Updated import
from geomas.world.spatial_manager import SpatialManager

class GenesisEngine:
    """
    Simulates 'Ancient History' deterministically to populate the Trust Matrix
    and provide context before the LLM agents take over.
    """

    # OPTIMIZED CONFIGURATION (Genetic Algorithm Result)
    # Target: High=15%, Low=20%, Mid=65%
    # Error: 0.000062
    DEFAULT_CONFIG = {
        "base_friction": 0.2832,
        "trade_bonus": 0.1222,
        "conflict_penalty": 0.1425,
        "alliance_threshold": 0.7201,
        "rivalry_threshold": 0.3427,
        "decay_rate": 0.0082,
        "resource_envy_penalty": 0.0525,
        "alliance_chance": 0.2717,
        "rivalry_chance": 0.1111
    }

    def __init__(self, world: WorldState, seed: int = 42, config: Dict[str, float] = None):
        self.world = world
        self.spatial = SpatialManager(world)
        self.rng = np.random.RandomState(seed)
        self.history_log: List[str] = []
        self.alliances: Dict[Tuple[str, str], bool] = {}
        
        # Load config or defaults
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)

    def initialize_history(self, years: int = 50):
        """Runs a fast-forward simulation of N years."""
        print(f"Genesis: Simulating {years} years of history...")
        
        nation_ids = list(self.world.nations.keys())
        
        for n_a in nation_ids:
            if n_a not in self.world.trust_matrix:
                self.world.trust_matrix[n_a] = {}
            for n_b in nation_ids:
                if n_a == n_b:
                    self.world.trust_matrix[n_a][n_b] = 1.0
                else:
                    self.world.trust_matrix[n_a][n_b] = 0.5

        for year in range(1, years + 1):
            self._simulate_year(year)

        self.world.global_events = self.history_log
        print(f"Genesis Complete. Generated {len(self.history_log)} historical events.")

    def _simulate_year(self, year: int):
        nation_ids = list(self.world.nations.keys())
        self.rng.shuffle(nation_ids)
        processed_pairs = set()

        for i in range(len(nation_ids)):
            for j in range(i + 1, len(nation_ids)):
                n_a = nation_ids[i]
                n_b = nation_ids[j]
                
                pair_key = tuple(sorted((n_a, n_b)))
                if pair_key in processed_pairs: continue
                processed_pairs.add(pair_key)

                if pair_key not in self.alliances:
                    self._apply_trust_decay(n_a, n_b)

                self._process_interaction(n_a, n_b, year)
                self._check_diplomatic_shifts(n_a, n_b, year)

    def _apply_trust_decay(self, n_a: str, n_b: str):
        current = self.world.trust_matrix[n_a][n_b]
        rate = self.config["decay_rate"]
        if current > 0.5:
            self._update_trust(n_a, n_b, -rate) 
        elif current < 0.5:
            self._update_trust(n_a, n_b, +rate) 

    def _check_diplomatic_shifts(self, n_a: str, n_b: str, year: int):
        current = self.world.trust_matrix[n_a][n_b]
        pair_key = tuple(sorted((n_a, n_b)))
        
        if current > self.config["alliance_threshold"] and pair_key not in self.alliances:
            if self.rng.rand() < self.config["alliance_chance"]:
                self.alliances[pair_key] = True
                self._update_trust(n_a, n_b, 0.20)
                self._log_event(year, f"Formal ALLIANCE signed between {self._name(n_a)} and {self._name(n_b)}.", "ALLIANCE")
        
        if current < 0.4 and pair_key in self.alliances:
            del self.alliances[pair_key]
            self._log_event(year, f"Alliance BROKEN between {self._name(n_a)} and {self._name(n_b)}.", "BETRAYAL")

        if current < self.config["rivalry_threshold"]:
             if self.rng.rand() < self.config["rivalry_chance"]:
                 self._update_trust(n_a, n_b, -0.10)

    def _process_interaction(self, n_a: str, n_b: str, year: int):
        is_neighbor = n_b in self.spatial.get_neighboring_nations(n_a)
        if is_neighbor:
            self._handle_border_dynamics(n_a, n_b, year)
        self._handle_trade_dynamics(n_a, n_b, year)

    def _handle_border_dynamics(self, n_a: str, n_b: str, year: int):
        friction_prob = self.config["base_friction"]
        
        border_provs_a = self.spatial.get_border_provinces(n_a)
        mountain_segments = 0
        total_segments = 0
        
        for p_id in border_provs_a:
            prov = self.world.provinces[p_id]
            for n_id in prov.neighbors:
                neighbor = self.world.provinces.get(n_id)
                if neighbor and neighbor.owner_id == n_b:
                    total_segments += 1
                    if prov.terrain == TerrainType.MOUNTAIN:
                        mountain_segments += 1
        
        if total_segments > 0:
            mountain_ratio = mountain_segments / total_segments
            friction_prob -= (mountain_ratio * 0.08) 
        
        current_trust = self.world.trust_matrix[n_a][n_b]
        if current_trust < 0.4:
            friction_prob += 0.10 
        elif current_trust > 0.8:
            friction_prob -= 0.10 
        
        if self.rng.rand() < friction_prob:
            self._update_trust(n_a, n_b, -self.config["conflict_penalty"]) 
            self._log_event(year, f"Border skirmish between {self._name(n_a)} and {self._name(n_b)}.", "CONFLICT")

    def _handle_trade_dynamics(self, n_a: str, n_b: str, year: int):
        res_a = self._get_total_resources(n_a)
        res_b = self._get_total_resources(n_b)
        
        complementarity = 0.0
        if abs(res_a['energy'] - res_b['energy']) > 800: complementarity += 0.05
        if abs(res_a['food'] - res_b['food']) > 800: complementarity += 0.05
            
        current_trust = self.world.trust_matrix[n_a][n_b]
        if current_trust > 0.4: complementarity += 0.02
        else: complementarity -= 0.10 
            
        total_a = sum(res_a.values())
        total_b = sum(res_b.values())
        if abs(total_a - total_b) > 2000:
            complementarity -= 0.05
            if self.rng.rand() < 0.05:
                self._update_trust(n_a, n_b, -self.config["resource_envy_penalty"])

        if self.rng.rand() < complementarity:
            self._update_trust(n_a, n_b, self.config["trade_bonus"]) 
            if self.rng.rand() < 0.2: 
                self._log_event(year, f"Trade agreement signed between {self._name(n_a)} and {self._name(n_b)}.", "TRADE")

    def _update_trust(self, n_a: str, n_b: str, delta: float):
        val = self.world.trust_matrix[n_a][n_b] + delta
        val = max(0.0, min(1.0, val)) 
        self.world.trust_matrix[n_a][n_b] = val
        self.world.trust_matrix[n_b][n_a] = val

    def _get_total_resources(self, n_id: str) -> Dict[str, float]:
        nation = self.world.nations[n_id]
        totals = {'energy': 0.0, 'food': 0.0, 'materials': 0.0}
        for p_id in nation.province_ids:
            prov = self.world.provinces[p_id]
            totals['energy'] += prov.energy_production
            totals['food'] += prov.food_production
            totals['materials'] += prov.materials_production
        return totals

    def _name(self, n_id: str) -> str:
        return self.world.nations[n_id].name

    def _log_event(self, year: int, text: str, tag: str):
        self.history_log.append(f"[Year {year}] [{tag}] {text}")
