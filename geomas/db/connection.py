"""
Database Connection Management.

Provides SimulationDB class for managing DuckDB connections and operations.
"""

import duckdb
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class SimulationDB:
    """
    Main database interface for simulation persistence.
    
    Manages a DuckDB database file for storage of MULTIPLE simulation runs.
    Each run is identified by a progressive `simulation_id` (INTEGER).
    
    Tables:
    - simulation: Metadata (id, uuid, seeds, etc.)
    - snapshots: World state per turn per sim
    - envelopes: Agent actions per turn per sim
    - behaviors: Metrics per turn per sim
    """
    
    def __init__(self, db_path: str, read_only: bool = False):
        """
        Initialize database connection.
        """
        self.db_path = Path(db_path)
        self.read_only = read_only
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Lazy connection initialization."""
        if self._conn is None:
            # If reading, we don't want to create/lock exclusively if possible
            # DuckDB locking: multiple readers OK, one writer BLOCKS ALL.
            self._conn = duckdb.connect(str(self.db_path), read_only=self.read_only)
        return self._conn
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
    
    def initialize(self) -> None:
        """
        Create schema tables if they don't exist.
        Now supports MULTI-SIMULATION schema.
        """
        # 1. Simulation Metadata
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS simulation (
                id INTEGER PRIMARY KEY, -- Progressive ID (1, 2, 3...)
                uuid VARCHAR,           -- Unique UUID for reference
                genesis_seed INTEGER,
                simulation_seed INTEGER,
                n_cells INTEGER,
                n_nations INTEGER,
                created_at TIMESTAMP,
                completed_at TIMESTAMP,
                total_turns INTEGER DEFAULT 0,
                name VARCHAR,           -- Optional friendly name
                scenario_json JSON      -- Planned scenarios metadata
            )
        """)
        
        # 2. Snapshots (World State)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                simulation_id INTEGER,
                turn INTEGER,
                provinces_json JSON,
                nations_json JSON,
                trust_matrix JSON,
                relationship_matrix JSON,
                world_events_json JSON,
                memory_json JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (simulation_id, turn),
                FOREIGN KEY (simulation_id) REFERENCES simulation(id)
            )
        """)
        
        # 3. Envelopes (Agent Actions)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS envelopes (
                simulation_id INTEGER,
                turn INTEGER,
                nation_id VARCHAR,
                envelope_json JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (simulation_id, turn, nation_id),
                FOREIGN KEY (simulation_id) REFERENCES simulation(id)
            )
        """)
        
        # 4. Behaviors (Metrics)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS behaviors (
                simulation_id INTEGER,
                turn INTEGER,
                nation_id VARCHAR,
                deception_total FLOAT,
                deception_defense FLOAT,
                deception_foreign FLOAT,
                coherence_score FLOAT,
                global_strategy VARCHAR,
                government_type VARCHAR,
                PRIMARY KEY (simulation_id, turn, nation_id),
                FOREIGN KEY (simulation_id) REFERENCES simulation(id)
            )
        """)
        
        # Migration: Add government_type if missing (RQ2)
        cols = self.conn.execute("PRAGMA table_info('behaviors')").fetchall()
        col_names = [c[1] for c in cols]
        if "government_type" not in col_names:
            print("[DB] Migrating: Adding 'government_type' to 'behaviors' table")
            self.conn.execute("ALTER TABLE behaviors ADD COLUMN government_type VARCHAR")
            
        # Migration for simulation table: add scenario_json if missing
        sim_cols = self.conn.execute("PRAGMA table_info('simulation')").fetchall()
        sim_col_names = [c[1] for c in sim_cols]
        if "scenario_json" not in sim_col_names:
            print("[DB] Migrating: Adding 'scenario_json' to 'simulation' table")
            self.conn.execute("ALTER TABLE simulation ADD COLUMN scenario_json JSON")
        
        # 5. Token Usage (Cost Tracking)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                simulation_id INTEGER,
                turn INTEGER,
                nation_id VARCHAR,
                agent_type VARCHAR,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                model VARCHAR,
                cost FLOAT,
                PRIMARY KEY (simulation_id, turn, nation_id, agent_type),
                FOREIGN KEY (simulation_id) REFERENCES simulation(id)
            )
        """)

    def create_simulation(
        self, 
        genesis_seed: int, 
        simulation_seed: int, 
        n_cells: int,
        n_nations: int,
        name: Optional[str] = None,
        scenario_json: Optional[str] = None
    ) -> int:
        """
        Create a new simulation entry and return its ID.
        Auto-increments from the last max ID.
        """
        # Get next ID
        result = self.conn.execute("SELECT MAX(id) FROM simulation").fetchone()
        next_id = 1
        if result and result[0] is not None:
            next_id = result[0] + 1
            
        sim_uuid = str(uuid.uuid4())
        
        self.conn.execute("""
            INSERT INTO simulation 
            (id, uuid, genesis_seed, simulation_seed, n_cells, n_nations, created_at, name, scenario_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?::JSON)
        """, [
            next_id,
            sim_uuid,
            genesis_seed,
            simulation_seed,
            n_cells,
            n_nations,
            datetime.now(),
            name or f"Simulation {next_id}",
            scenario_json
        ])
        
        return next_id
    
    def update_simulation_scenario(self, simulation_id: int, scenario_json: Optional[str]) -> None:
        """Update the planned scenario metadata for a simulation."""
        self.conn.execute("""
            UPDATE simulation SET scenario_json = ?::JSON WHERE id = ?
        """, [scenario_json, simulation_id])
    
    def get_simulations(self) -> List[Dict[str, Any]]:
        """List all simulations in the DB."""
        results = self.conn.execute("""
            SELECT id, name, created_at, total_turns, genesis_seed 
            FROM simulation 
            ORDER BY id DESC
        """).fetchall()
        
        return [
            {
                "id": row[0],
                "name": row[1],
                "created_at": row[2],
                "total_turns": row[3],
                "seed": row[4]
            }
            for row in results
        ]

    # --- SAVE METHODS (Require simulation_id) ---

    def save_snapshot(
        self,
        simulation_id: int,
        turn: int,
        provinces_json: str,
        nations_json: str,
        trust_matrix_json: str,
        relationship_matrix_json: str,
        world_events_json: str,
        memory_json: str
    ) -> None:
        """Save world state snapshot."""
        self.conn.execute("""
            INSERT OR REPLACE INTO snapshots 
            (simulation_id, turn, provinces_json, nations_json, trust_matrix, relationship_matrix, world_events_json, memory_json)
            VALUES (?, ?, ?::JSON, ?::JSON, ?::JSON, ?::JSON, ?::JSON, ?::JSON)
        """, [simulation_id, turn, provinces_json, nations_json, trust_matrix_json, relationship_matrix_json, world_events_json, memory_json])
        
        # Update total turns metadata
        self.conn.execute("""
            UPDATE simulation SET total_turns = ? WHERE id = ?
        """, [turn, simulation_id])
    
    def save_envelope(
        self,
        simulation_id: int,
        turn: int,
        nation_id: str,
        envelope_json: str
    ) -> None:
        """Save agent envelope."""
        self.conn.execute("""
            INSERT OR REPLACE INTO envelopes (simulation_id, turn, nation_id, envelope_json)
            VALUES (?, ?, ?, ?::JSON)
        """, [simulation_id, turn, nation_id, envelope_json])
    
    def save_behavior(
        self,
        simulation_id: int,
        turn: int,
        nation_id: str,
        deception_total: float,
        deception_defense: float,
        deception_foreign: float,
        coherence_score: float,
        global_strategy: str,
        government_type: str = None
    ) -> None:
        """Save behavior metrics (defense + foreign deception only)."""
        self.conn.execute("""
            INSERT OR REPLACE INTO behaviors 
            (simulation_id, turn, nation_id, deception_total, deception_defense, 
             deception_foreign, coherence_score, global_strategy, government_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            simulation_id, turn, nation_id, deception_total, deception_defense,
            deception_foreign, coherence_score, global_strategy, government_type
        ])

    def save_token_usage(
        self,
        simulation_id: int,
        turn: int,
        nation_id: str,
        agent_type: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        model: str,
        cost: float
    ) -> None:
        """Save token usage."""
        self.conn.execute("""
            INSERT OR REPLACE INTO token_usage 
            (simulation_id, turn, nation_id, agent_type, prompt_tokens, completion_tokens, total_tokens, model, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [simulation_id, turn, nation_id, agent_type, prompt_tokens, completion_tokens, total_tokens, model, cost])

    # --- LOAD METHODS (Require simulation_id) ---
    
    def load_snapshot(self, simulation_id: int, turn: int) -> Optional[dict]:
        """Load snapshot for specific sim and turn."""
        result = self.conn.execute("""
            SELECT provinces_json, nations_json, trust_matrix, relationship_matrix, world_events_json, memory_json
            FROM snapshots 
            WHERE simulation_id = ? AND turn = ?
        """, [simulation_id, turn]).fetchone()
        
        if result is None:
            return None
        
        return {
            "provinces_json": result[0],
            "nations_json": result[1],
            "trust_matrix": result[2],
            "relationship_matrix": result[3],
            "world_events_json": result[4],
            "memory_json": result[5]
        }
    
    def load_envelopes(self, simulation_id: int, turn: int) -> list:
        """Load envelopes for specific sim and turn."""
        results = self.conn.execute("""
            SELECT nation_id, envelope_json 
            FROM envelopes 
            WHERE simulation_id = ? AND turn = ?
        """, [simulation_id, turn]).fetchall()
        
        return [(row[0], row[1]) for row in results]
    
    def load_behaviors(self, simulation_id: int, turn: int) -> list:
        """Load behaviors for specific sim and turn."""
        results = self.conn.execute("""
            SELECT nation_id, deception_total, deception_defense, 
                   deception_foreign, coherence_score, global_strategy, government_type
            FROM behaviors 
            WHERE simulation_id = ? AND turn = ?
        """, [simulation_id, turn]).fetchall()
        
        return [
            {
                "nation_id": row[0],
                "deception_total": row[1],
                "deception_defense": row[2],
                "deception_foreign": row[3],
                "coherence_score": row[4],
                "global_strategy": row[5],
                "government_type": row[6]
            }
            for row in results
        ]

    def get_max_turn(self, simulation_id: int) -> int:
        """Get max turn for a specific simulation."""
        result = self.conn.execute("""
            SELECT MAX(turn) FROM snapshots WHERE simulation_id = ?
        """, [simulation_id]).fetchone()
        return result[0] if result and result[0] is not None else 0
    
    def get_simulation_info(self, simulation_id: int) -> Optional[dict]:
        """Get metadata for a specific simulation."""
        result = self.conn.execute("""
            SELECT id, genesis_seed, simulation_seed, n_cells, n_nations, created_at, total_turns, name, scenario_json
            FROM simulation WHERE id = ?
        """, [simulation_id]).fetchone()
        
        if result is None:
            return None
        
        return {
            "id": result[0],
            "genesis_seed": result[1],
            "simulation_seed": result[2],
            "n_cells": result[3],
            "n_nations": result[4],
            "created_at": result[5],
            "total_turns": result[6],
            "name": result[7],
            "scenario_json": result[8]
        }

    def copy_history_for_fork(self, source_sim_id: int, target_sim_id: int, up_to_turn: int) -> None:
        """
        Copies all records from source to target simulation up to a specific turn.
        Used for proper forking.
        """
        # 1. Snapshots
        self.conn.execute("""
            INSERT INTO snapshots 
            (simulation_id, turn, provinces_json, nations_json, trust_matrix, relationship_matrix, world_events_json, memory_json)
            SELECT ?, turn, provinces_json, nations_json, trust_matrix, relationship_matrix, world_events_json, memory_json
            FROM snapshots 
            WHERE simulation_id = ? AND turn <= ?
        """, [target_sim_id, source_sim_id, up_to_turn])
        
        # 2. Envelopes
        self.conn.execute("""
            INSERT INTO envelopes (simulation_id, turn, nation_id, envelope_json)
            SELECT ?, turn, nation_id, envelope_json
            FROM envelopes 
            WHERE simulation_id = ? AND turn <= ?
        """, [target_sim_id, source_sim_id, up_to_turn])
        
        # 3. Behaviors
        self.conn.execute("""
            INSERT INTO behaviors 
            (simulation_id, turn, nation_id, deception_total, deception_defense, 
             deception_foreign, coherence_score, global_strategy, government_type)
            SELECT ?, turn, nation_id, deception_total, deception_defense, 
                   deception_foreign, coherence_score, global_strategy, government_type
            FROM behaviors 
            WHERE simulation_id = ? AND turn <= ?
        """, [target_sim_id, source_sim_id, up_to_turn])
        
        # 4. Token Usage
        self.conn.execute("""
            INSERT INTO token_usage 
            (simulation_id, turn, nation_id, agent_type, prompt_tokens, completion_tokens, total_tokens, model, cost)
            SELECT ?, turn, nation_id, agent_type, prompt_tokens, completion_tokens, total_tokens, model, cost
            FROM token_usage 
            WHERE simulation_id = ? AND turn <= ?
        """, [target_sim_id, source_sim_id, up_to_turn])

        # 5. Update total_turns in simulation table for the target
        self.conn.execute("""
            UPDATE simulation SET total_turns = ? WHERE id = ?
        """, [up_to_turn, target_sim_id])

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
