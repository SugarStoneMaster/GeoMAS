"""
Database Connection Management.

Provides SimulationDB class for managing DuckDB connections and operations.
"""

import duckdb
from pathlib import Path
from typing import Optional
from datetime import datetime
import uuid


class SimulationDB:
    """
    Main database interface for simulation persistence.
    
    Manages a DuckDB database file for storing simulation snapshots,
    agent decisions (envelopes), and behavior metrics.
    
    Usage:
        db = SimulationDB("data/sim_001.duckdb")
        db.initialize()  # Create tables
        
        # Save data each turn
        db.save_snapshot(turn, provinces, nations, trust, relations)
        db.save_envelope(turn, nation_id, envelope_dict)
        db.save_behavior(turn, nation_id, scores)
        
        # Query data
        snapshot = db.load_snapshot(turn)
        envelopes = db.load_envelopes(turn)
    """
    
    def __init__(self, db_path: str, simulation_id: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to DuckDB file (created if not exists)
            simulation_id: Optional UUID, generated if not provided
        """
        self.db_path = Path(db_path)
        self.simulation_id = simulation_id or str(uuid.uuid4())
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Lazy connection initialization."""
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path))
        return self._conn
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
    
    def initialize(
        self, 
        genesis_seed: int, 
        simulation_seed: int, 
        n_cells: int
    ) -> None:
        """
        Create tables and insert simulation metadata.
        
        Args:
            genesis_seed: Seed used for world generation
            simulation_seed: Seed used for simulation randomness
            n_cells: Number of provinces in the world
        """
        # Create tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS simulation (
                id VARCHAR PRIMARY KEY,
                genesis_seed INTEGER,
                simulation_seed INTEGER,
                n_cells INTEGER,
                created_at TIMESTAMP,
                completed_at TIMESTAMP,
                total_turns INTEGER DEFAULT 0
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                turn INTEGER PRIMARY KEY,
                provinces_json JSON,
                nations_json JSON,
                trust_matrix JSON,
                relationship_matrix JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS envelopes (
                turn INTEGER,
                nation_id VARCHAR,
                envelope_json JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (turn, nation_id)
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS behaviors (
                turn INTEGER,
                nation_id VARCHAR,
                deception_total FLOAT,
                deception_defense FLOAT,
                deception_economic FLOAT,
                deception_foreign FLOAT,
                coherence_score FLOAT,
                global_strategy VARCHAR,
                PRIMARY KEY (turn, nation_id)
            )
        """)
        
        # Insert simulation metadata
        self.conn.execute("""
            INSERT OR REPLACE INTO simulation 
            (id, genesis_seed, simulation_seed, n_cells, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, [
            self.simulation_id,
            genesis_seed,
            simulation_seed,
            n_cells,
            datetime.now()
        ])
    
    def save_snapshot(
        self,
        turn: int,
        provinces_json: str,
        nations_json: str,
        trust_matrix_json: str,
        relationship_matrix_json: str
    ) -> None:
        """
        Save world state snapshot for a turn.
        
        Args:
            turn: Turn number
            provinces_json: JSON string of provinces list
            nations_json: JSON string of nations list
            trust_matrix_json: JSON string of trust matrix
            relationship_matrix_json: JSON string of relationship matrix
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO snapshots 
            (turn, provinces_json, nations_json, trust_matrix, relationship_matrix)
            VALUES (?, ?::JSON, ?::JSON, ?::JSON, ?::JSON)
        """, [turn, provinces_json, nations_json, trust_matrix_json, relationship_matrix_json])
        
        # Update total turns
        self.conn.execute("""
            UPDATE simulation SET total_turns = ? WHERE id = ?
        """, [turn, self.simulation_id])
    
    def save_envelope(
        self,
        turn: int,
        nation_id: str,
        envelope_json: str
    ) -> None:
        """
        Save agent decision envelope for a turn.
        
        Args:
            turn: Turn number
            nation_id: Nation identifier
            envelope_json: JSON string of CountryEnvelope
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO envelopes (turn, nation_id, envelope_json)
            VALUES (?, ?, ?::JSON)
        """, [turn, nation_id, envelope_json])
    
    def save_behavior(
        self,
        turn: int,
        nation_id: str,
        deception_total: float,
        deception_defense: float,
        deception_economic: float,
        deception_foreign: float,
        coherence_score: float,
        global_strategy: str
    ) -> None:
        """
        Save behavior metrics for a nation at a turn.
        
        Args:
            turn: Turn number
            nation_id: Nation identifier
            deception_*: Deception scores per domain
            coherence_score: Strategic coherence score
            global_strategy: Strategy enum value as string
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO behaviors 
            (turn, nation_id, deception_total, deception_defense, 
             deception_economic, deception_foreign, coherence_score, global_strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            turn, nation_id, deception_total, deception_defense,
            deception_economic, deception_foreign, coherence_score, global_strategy
        ])
    
    def load_snapshot(self, turn: int) -> Optional[dict]:
        """
        Load world state snapshot for a turn.
        
        Returns:
            Dict with provinces_json, nations_json, trust_matrix, relationship_matrix
            or None if turn not found.
        """
        result = self.conn.execute("""
            SELECT provinces_json, nations_json, trust_matrix, relationship_matrix
            FROM snapshots WHERE turn = ?
        """, [turn]).fetchone()
        
        if result is None:
            return None
        
        return {
            "provinces_json": result[0],
            "nations_json": result[1],
            "trust_matrix": result[2],
            "relationship_matrix": result[3]
        }
    
    def load_envelopes(self, turn: int) -> list:
        """
        Load all agent envelopes for a turn.
        
        Returns:
            List of (nation_id, envelope_json) tuples
        """
        results = self.conn.execute("""
            SELECT nation_id, envelope_json FROM envelopes WHERE turn = ?
        """, [turn]).fetchall()
        
        return [(row[0], row[1]) for row in results]
    
    def load_behaviors(self, turn: int) -> list:
        """
        Load all behavior records for a turn.
        
        Returns:
            List of behavior dicts
        """
        results = self.conn.execute("""
            SELECT nation_id, deception_total, deception_defense, 
                   deception_economic, deception_foreign, coherence_score, global_strategy
            FROM behaviors WHERE turn = ?
        """, [turn]).fetchall()
        
        return [
            {
                "nation_id": row[0],
                "deception_total": row[1],
                "deception_defense": row[2],
                "deception_economic": row[3],
                "deception_foreign": row[4],
                "coherence_score": row[5],
                "global_strategy": row[6]
            }
            for row in results
        ]
    
    def get_behavior_timeline(self, nation_id: str):
        """
        Get behavior metrics over time for a nation.
        
        Returns:
            Pandas DataFrame with turn, deception scores, coherence
        """
        return self.conn.execute("""
            SELECT turn, deception_total, deception_defense, 
                   deception_economic, deception_foreign, coherence_score
            FROM behaviors 
            WHERE nation_id = ?
            ORDER BY turn
        """, [nation_id]).df()
    
    def get_simulation_info(self) -> Optional[dict]:
        """Get simulation metadata."""
        result = self.conn.execute("""
            SELECT id, genesis_seed, simulation_seed, n_cells, created_at, total_turns
            FROM simulation WHERE id = ?
        """, [self.simulation_id]).fetchone()
        
        if result is None:
            return None
        
        return {
            "id": result[0],
            "genesis_seed": result[1],
            "simulation_seed": result[2],
            "n_cells": result[3],
            "created_at": result[4],
            "total_turns": result[5]
        }
    
    def export_behaviors_csv(self, path: str) -> None:
        """Export behaviors table to CSV."""
        self.conn.execute(f"""
            COPY behaviors TO '{path}' (HEADER, DELIMITER ',')
        """)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
