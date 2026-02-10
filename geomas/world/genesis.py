"""
Genesis Engine.

Simulates 'Ancient History' deterministically to populate the Trust Matrix
and provide context before the LLM agents take over.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from geomas.schemas.world import WorldState, TerrainType
from geomas.world.spatial import SpatialManager


class GenesisEngine:
    """
    Simulates 'Ancient History' deterministically to populate the Trust Matrix
    and provide context before the LLM agents take over.
    
    Optionally persists events to GenesisDB for reuse.
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

    def __init__(
        self, 
        world: WorldState, 
        seed: int = 42, 
        config: Dict[str, float] = None,
        db_path: Optional[str] = None
    ):
        """
        Initialize GenesisEngine.
        
        Args:
            world: WorldState to populate
            seed: RNG seed for deterministic history
            config: Optional config overrides
            db_path: Optional path to GenesisDB file for persistence
        """
        self.world = world
        self.spatial = SpatialManager(world)
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.history_log: List[str] = []
        self.alliances: Dict[Tuple[str, str], bool] = {}
        
        # Structured events for DB storage
        self._events: List[Dict[str, Any]] = []
        self._event_counter = 0
        
        # Load config or defaults
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # Optional database persistence
        self.db = None
        self.db_path = db_path

    def initialize_history(self, years: int = 50):
        """Runs a fast-forward simulation of N years."""
        print(f"Genesis: Simulating {years} years of history...")
        
        nation_ids = list(self.world.nations.keys())
        
        for n_a in nation_ids:
            if n_a not in self.world.trust_matrix:
                self.world.trust_matrix[n_a] = {}
            if n_a not in self.world.relationship_matrix:
                self.world.relationship_matrix[n_a] = {}
            for n_b in nation_ids:
                if n_a == n_b:
                    self.world.trust_matrix[n_a][n_b] = 100  # Self-trust
                else:
                    self.world.trust_matrix[n_a][n_b] = 50  # Neutral
                    # Default relationship: PEACE with everyone
                    self.world.relationship_matrix[n_a][n_b] = "PEACE"

        for year in range(1, years + 1):
            self._simulate_year(year)

        self.world.global_events = self.history_log
        
        # Persist to DB if path provided
        if self.db_path:
            self._persist_to_db(years)
        
        print(f"Genesis Complete. Generated {len(self.history_log)} historical events.")

    def _persist_to_db(self, years: int) -> None:
        """Save genesis data to database."""
        from geomas.db import GenesisDB
        
        self.db = GenesisDB(self.db_path)
        self.db.initialize(
            seed=self.seed,
            years=years,
            n_nations=len(self.world.nations),
            config=self.config
        )
        
        # Convert events to tuple format for batch insert
        event_tuples = [
            (e["id"], e["year"], e["tag"], e["description"], e["nation_a"], e["nation_b"])
            for e in self._events
        ]
        self.db.save_events_batch(event_tuples)
        
        # Save final trust matrix
        self.db.save_trust_matrix(self.world.trust_matrix)
        
        # Save active alliances
        self.db.save_alliances(self.alliances)
        
        print(f"Genesis persisted to {self.db_path}")

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
        rate = self.config["decay_rate"] * 100  # Scale to 0-100
        if current > 50:
            self._update_trust(n_a, n_b, -rate) 
        elif current < 50:
            self._update_trust(n_a, n_b, +rate) 

    def _check_diplomatic_shifts(self, n_a: str, n_b: str, year: int):
        current = self.world.trust_matrix[n_a][n_b]
        pair_key = tuple(sorted((n_a, n_b)))
        
        # Scale thresholds to 0-100
        alliance_thresh = self.config["alliance_threshold"] * 100
        rivalry_thresh = self.config["rivalry_threshold"] * 100
        
        if current > alliance_thresh and pair_key not in self.alliances:
            if self.rng.rand() < self.config["alliance_chance"]:
                self.alliances[pair_key] = True
                self._update_trust(n_a, n_b, 20)  # +20 trust
                self._log_event(
                    year, 
                    f"🤝 Formal ALLIANCE signed between {self._name(n_a)} and {self._name(n_b)}.", 
                    "ALLIANCE",
                    n_a, n_b
                )
        
        if current < 40 and pair_key in self.alliances:
            del self.alliances[pair_key]
            self._log_event(
                year, 
                f"💔 Alliance BROKEN between {self._name(n_a)} and {self._name(n_b)}.", 
                "BETRAYAL",
                n_a, n_b
            )

        if current < rivalry_thresh:
             if self.rng.rand() < self.config["rivalry_chance"]:
                 self._update_trust(n_a, n_b, -10)  # -10 trust

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
        if current_trust < 40:
            friction_prob += 0.10 
        elif current_trust > 80:
            friction_prob -= 0.10 
        
        if self.rng.rand() < friction_prob:
            self._update_trust(n_a, n_b, -self.config["conflict_penalty"] * 100)  # Scale penalty
            self._log_event(
                year, 
                f"⚔️ Border skirmish between {self._name(n_a)} and {self._name(n_b)}.", 
                "CONFLICT",
                n_a, n_b
            )

    def _handle_trade_dynamics(self, n_a: str, n_b: str, year: int):
        res_a = self._get_total_resources(n_a)
        res_b = self._get_total_resources(n_b)
        
        complementarity = 0.0
        if abs(res_a['energy'] - res_b['energy']) > 800: complementarity += 0.05
        if abs(res_a['food'] - res_b['food']) > 800: complementarity += 0.05
            
        current_trust = self.world.trust_matrix[n_a][n_b]
        if current_trust > 40: complementarity += 0.02
        else: complementarity -= 0.10 
            
        total_a = sum(res_a.values())
        total_b = sum(res_b.values())
        if abs(total_a - total_b) > 2000:
            complementarity -= 0.05
            if self.rng.rand() < 0.05:
                self._update_trust(n_a, n_b, -self.config["resource_envy_penalty"] * 100)

        if self.rng.rand() < complementarity:
            self._update_trust(n_a, n_b, self.config["trade_bonus"] * 100)  # Scale bonus
            if self.rng.rand() < 0.2: 
                self._log_event(
                    year, 
                    f"📦 Trade agreement signed between {self._name(n_a)} and {self._name(n_b)}.", 
                    "TRADE",
                    n_a, n_b
                )

    def _update_trust(self, n_a: str, n_b: str, delta: float):
        """Update trust from n_a towards n_b (asymmetric, 0-100 scale)."""
        val = self.world.trust_matrix[n_a][n_b] + delta
        val = max(0, min(100, val))  # Clamp 0-100
        self.world.trust_matrix[n_a][n_b] = val
        # Note: Trust is intentionally asymmetric - A trusting B doesn't mean B trusts A

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

    def _log_event(self, year: int, text: str, tag: str, nation_a: str = None, nation_b: str = None):
        """Log event to history and store structured data for DB."""
        self.history_log.append(f"📜 [Year {year}] [{tag}] {text}")
        
        # Store structured event for DB persistence
        self._event_counter += 1
        self._events.append({
            "id": self._event_counter,
            "year": year,
            "tag": tag,
            "description": text,
            "nation_a": nation_a,
            "nation_b": nation_b
        })
