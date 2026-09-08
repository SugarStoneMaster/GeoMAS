"""
Genesis Database.

Separate DuckDB file for storing historical events generated during genesis.
Can be reused across multiple simulations with the same seed.
"""

import duckdb
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class GenesisDB:
    """
    Database for storing genesis (historical) events.
    
    Stored separately from simulation DB to allow reuse across
    multiple simulation runs with the same genesis seed.
    
    File: data/genesis_{seed}.duckdb
    
    Usage:
        db = GenesisDB("data/genesis_42.duckdb")
        db.initialize(seed=42, years=50, n_nations=10)
        
        # Save events
        db.save_event(year=15, tag="ALLIANCE", description="...", nations=["A", "B"])
        
        # Query
        events = db.get_events_for_nation("nation_a")
        all_events = db.get_all_events()
    """
    
    def __init__(self, db_path: str):
        """
        Initialize connection to genesis database.
        
        Args:
            db_path: Path to DuckDB file (e.g., "data/genesis_42.duckdb")
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
    
    def initialize(
        self, 
        seed: int, 
        years: int = 50, 
        n_nations: int = 0,
        config: Optional[Dict[str, float]] = None
    ) -> None:
        """
        Create tables and store genesis metadata.
        
        Args:
            seed: Genesis RNG seed
            years: Number of simulated years
            n_nations: Number of nations at genesis
            config: Optional GenesisEngine config parameters
        """
        # Create tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS genesis_meta (
                seed INT PRIMARY KEY,
                years INT,
                n_nations INT,
                config JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INT PRIMARY KEY,
                year INT,
                tag VARCHAR,
                description VARCHAR,
                nation_a VARCHAR,
                nation_b VARCHAR
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS initial_trust (
                nation_a VARCHAR,
                nation_b VARCHAR,
                trust FLOAT,
                PRIMARY KEY (nation_a, nation_b)
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS alliances (
                nation_a VARCHAR,
                nation_b VARCHAR,
                PRIMARY KEY (nation_a, nation_b)
            )
        """)
        
        # Insert metadata
        import json
        self.conn.execute("""
            INSERT OR REPLACE INTO genesis_meta (seed, years, n_nations, config)
            VALUES (?, ?, ?, ?)
        """, [seed, years, n_nations, json.dumps(config) if config else None])
    
    def save_event(
        self, 
        event_id: int,
        year: int, 
        tag: str, 
        description: str, 
        nation_a: str,
        nation_b: Optional[str] = None
    ) -> None:
        """
        Save a single genesis event.
        
        Args:
            event_id: Unique event ID
            year: Year of event (1-50 typically)
            tag: Event type (ALLIANCE, BETRAYAL, CONFLICT, TRADE)
            description: Human-readable event description
            nation_a: First nation involved
            nation_b: Second nation involved (optional)
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO events (id, year, tag, description, nation_a, nation_b)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [event_id, year, tag, description, nation_a, nation_b])
    
    def save_events_batch(self, events: List[Tuple[int, int, str, str, str, Optional[str]]]) -> None:
        """
        Save multiple events at once.
        
        Args:
            events: List of (id, year, tag, description, nation_a, nation_b) tuples
        """
        self.conn.executemany("""
            INSERT OR REPLACE INTO events (id, year, tag, description, nation_a, nation_b)
            VALUES (?, ?, ?, ?, ?, ?)
        """, events)
    
    def save_trust_matrix(self, trust_matrix: Dict[str, Dict[str, float]]) -> None:
        """
        Save final trust matrix after genesis.
        
        Args:
            trust_matrix: Trust values between all nation pairs
        """
        rows = []
        for n_a, inner in trust_matrix.items():
            for n_b, trust in inner.items():
                if n_a != n_b:  # Skip self-trust
                    rows.append((n_a, n_b, trust))
        
        self.conn.executemany("""
            INSERT OR REPLACE INTO initial_trust (nation_a, nation_b, trust)
            VALUES (?, ?, ?)
        """, rows)
    
    def save_alliances(self, alliances: Dict[Tuple[str, str], bool]) -> None:
        """
        Save alliances formed during genesis.
        
        Args:
            alliances: Dict of (nation_a, nation_b) -> True for active alliances
        """
        rows = [(pair[0], pair[1]) for pair in alliances.keys()]
        self.conn.executemany("""
            INSERT OR REPLACE INTO alliances (nation_a, nation_b)
            VALUES (?, ?)
        """, rows)
    
    def get_all_events(self) -> List[Dict]:
        """Get all genesis events ordered by year."""
        results = self.conn.execute("""
            SELECT id, year, tag, description, nation_a, nation_b
            FROM events ORDER BY year, id
        """).fetchall()
        
        return [
            {
                "id": row[0],
                "year": row[1],
                "tag": row[2],
                "description": row[3],
                "nation_a": row[4],
                "nation_b": row[5]
            }
            for row in results
        ]
    
    def get_events_for_nation(self, nation_id: str) -> List[Dict]:
        """Get all events involving a specific nation."""
        results = self.conn.execute("""
            SELECT id, year, tag, description, nation_a, nation_b
            FROM events 
            WHERE nation_a = ? OR nation_b = ?
            ORDER BY year, id
        """, [nation_id, nation_id]).fetchall()
        
        return [
            {
                "id": row[0],
                "year": row[1],
                "tag": row[2],
                "description": row[3],
                "nation_a": row[4],
                "nation_b": row[5]
            }
            for row in results
        ]
    
    def get_events_by_tag(self, tag: str) -> List[Dict]:
        """Get all events of a specific type."""
        results = self.conn.execute("""
            SELECT id, year, tag, description, nation_a, nation_b
            FROM events WHERE tag = ?
            ORDER BY year, id
        """, [tag]).fetchall()
        
        return [
            {
                "id": row[0],
                "year": row[1],
                "tag": row[2],
                "description": row[3],
                "nation_a": row[4],
                "nation_b": row[5]
            }
            for row in results
        ]
    
    def get_trust_matrix(self) -> Dict[str, Dict[str, float]]:
        """Load initial trust matrix from DB."""
        results = self.conn.execute("""
            SELECT nation_a, nation_b, trust FROM initial_trust
        """).fetchall()
        
        matrix = {}
        for n_a, n_b, trust in results:
            if n_a not in matrix:
                matrix[n_a] = {}
            matrix[n_a][n_b] = trust
        
        return matrix
    
    def get_alliances(self) -> List[Tuple[str, str]]:
        """Get list of alliances from genesis."""
        results = self.conn.execute("""
            SELECT nation_a, nation_b FROM alliances
        """).fetchall()
        
        return [(row[0], row[1]) for row in results]
    
    def get_genesis_info(self) -> Optional[Dict]:
        """Get genesis metadata."""
        result = self.conn.execute("""
            SELECT seed, years, n_nations, config, created_at
            FROM genesis_meta LIMIT 1
        """).fetchone()
        
        if result is None:
            return None
        
        import json
        return {
            "seed": result[0],
            "years": result[1],
            "n_nations": result[2],
            "config": json.loads(result[3]) if result[3] else None,
            "created_at": result[4]
        }
    
    def event_count(self) -> int:
        """Get total number of events."""
        result = self.conn.execute("SELECT COUNT(*) FROM events").fetchone()
        return result[0] if result else 0
    
    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
