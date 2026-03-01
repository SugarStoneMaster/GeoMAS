"""
Metrics Database Module.

Handles the dedicated 'metrics.duckdb' database for telemetry and post-simulation analysis.
Separating metrics from the main functional database ensures fast time-series queries.
"""

import duckdb
import os
from typing import List, Dict, Any


class MetricsDB:
    def __init__(self, db_path: str = "metrics.duckdb"):
        """Initializes the metrics database and creates schemas if they don't exist."""
        self.db_path = db_path
        self._conn = None
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)) if os.path.dirname(db_path) else ".", exist_ok=True)
        
        self._create_tables()

    @property
    def conn(self):
        """Lazy connection initialization."""
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)
        return self._conn

    def _create_tables(self):
        """Creates the relational tables for metrics."""
        
        # 1. Nation-Level Metrics
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_metrics_nation_id;
            CREATE TABLE IF NOT EXISTS metrics_nation (
                id INTEGER DEFAULT nextval('seq_metrics_nation_id') PRIMARY KEY,
                simulation_id VARCHAR NOT NULL,
                turn INTEGER NOT NULL,
                nation_id VARCHAR NOT NULL,
                
                -- Agent Metrics
                deception_overall DOUBLE,
                deception_defense DOUBLE,
                deception_foreign DOUBLE,
                coherence_score DOUBLE,
                
                -- Resource Metrics
                budget DOUBLE,
                food DOUBLE,
                energy DOUBLE,
                materials DOUBLE,
                population DOUBLE,
                workers DOUBLE,
                
                -- Public & Military Metrics
                public_satisfaction DOUBLE,
                in_civil_unrest BOOLEAN,
                soldiers INTEGER,
                aircraft INTEGER,
                navy INTEGER,
                power_projection DOUBLE,
                
                -- Flow Metrics (Trade vs War)
                trade_volume DOUBLE,
                military_spending DOUBLE
            );
            
            CREATE INDEX IF NOT EXISTS idx_nation_sim_turn ON metrics_nation(simulation_id, turn);
        """)
        
        # 2. Global Aggregates
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_metrics_global_id;
            CREATE TABLE IF NOT EXISTS metrics_global (
                id INTEGER DEFAULT nextval('seq_metrics_global_id') PRIMARY KEY,
                simulation_id VARCHAR NOT NULL,
                turn INTEGER NOT NULL,
                
                global_deception_avg DOUBLE,
                global_coherence_avg DOUBLE,
                global_satisfaction_avg DOUBLE,
                
                territories_changed_hands INTEGER,
                units_created INTEGER,
                units_destroyed INTEGER,
                
                global_trade_volume DOUBLE
            );
            
            CREATE INDEX IF NOT EXISTS idx_global_sim_turn ON metrics_global(simulation_id, turn);
        """)
        
        # 3. Trust Network
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_metrics_trust_id;
            CREATE TABLE IF NOT EXISTS metrics_trust (
                id INTEGER DEFAULT nextval('seq_metrics_trust_id') PRIMARY KEY,
                simulation_id VARCHAR NOT NULL,
                turn INTEGER NOT NULL,
                observer_id VARCHAR NOT NULL,
                target_id VARCHAR NOT NULL,
                
                trust_value DOUBLE,
                relationship_state VARCHAR
            );
            
            CREATE INDEX IF NOT EXISTS idx_trust_sim_turn ON metrics_trust(simulation_id, turn);
        """)

        # 4. Action Outcomes (engine-level accept/reject per individual action)
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_metrics_action_outcomes_id;
            CREATE TABLE IF NOT EXISTS metrics_action_outcomes (
                id          INTEGER DEFAULT nextval('seq_metrics_action_outcomes_id') PRIMARY KEY,
                simulation_id VARCHAR NOT NULL,
                turn          INTEGER NOT NULL,
                nation_id     VARCHAR NOT NULL,
                domain        VARCHAR NOT NULL,
                action_type   VARCHAR NOT NULL,
                status        VARCHAR NOT NULL,
                reason        VARCHAR
            );
            CREATE INDEX IF NOT EXISTS idx_action_outcomes_sim_turn
                ON metrics_action_outcomes(simulation_id, turn);
        """)

        # 5. Presidential Decisions (president APPROVE/VETO per domain per turn)
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_metrics_pres_decisions_id;
            CREATE TABLE IF NOT EXISTS metrics_presidential_decisions (
                id          INTEGER DEFAULT nextval('seq_metrics_pres_decisions_id') PRIMARY KEY,
                simulation_id VARCHAR NOT NULL,
                turn          INTEGER NOT NULL,
                nation_id     VARCHAR NOT NULL,
                domain        VARCHAR NOT NULL,
                decision      VARCHAR NOT NULL,
                action_type   VARCHAR,
                reasoning     VARCHAR
            );
            CREATE INDEX IF NOT EXISTS idx_pres_decisions_sim_turn
                ON metrics_presidential_decisions(simulation_id, turn);
        """)

    def insert_nation_metrics(self, simulation_id: str, metrics_list: List[Dict[str, Any]]):
        """Batch inserts nation-level metrics."""
        if not metrics_list:
            return
            
        # Ensure simulation_id is injected
        for m in metrics_list:
            m['simulation_id'] = simulation_id
            
        df = self.conn.execute("SELECT * FROM metrics_nation LIMIT 0").df()
        
        # Using parameterized insert for safety and speed
        insert_query = """
            INSERT INTO metrics_nation (
                simulation_id, turn, nation_id, 
                deception_overall, deception_defense, deception_foreign, coherence_score,
                budget, food, energy, materials, population, workers,
                public_satisfaction, in_civil_unrest, soldiers, aircraft, navy, power_projection,
                trade_volume, military_spending
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Prepare data tuples
        data = [
            (
                m.get('simulation_id'), m.get('turn'), m.get('nation_id'),
                m.get('deception_overall', 0.0), m.get('deception_defense', 0.0), 
                m.get('deception_foreign', 0.0), 
                m.get('coherence_score', 1.0),
                m.get('budget', 0.0), m.get('food', 0.0), m.get('energy', 0.0), 
                m.get('materials', 0.0), m.get('population', 0.0), m.get('workers', 0.0),
                m.get('public_satisfaction', 50.0), m.get('in_civil_unrest', False),
                m.get('soldiers', 0), m.get('aircraft', 0), m.get('navy', 0), 
                m.get('power_projection', 0.0),
                m.get('trade_volume', 0.0), m.get('military_spending', 0.0)
            )
            for m in metrics_list
        ]
        
        self.conn.executemany(insert_query, data)

    def insert_global_metrics(self, simulation_id: str, turn: int, global_data: Dict[str, Any]):
        """Inserts global aggregate metrics for a given turn."""
        insert_query = """
            INSERT INTO metrics_global (
                simulation_id, turn,
                global_deception_avg, global_coherence_avg, global_satisfaction_avg,
                territories_changed_hands, units_created, units_destroyed, global_trade_volume
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.conn.execute(insert_query, (
            simulation_id,
            turn,
            global_data.get('global_deception_avg', 0.0),
            global_data.get('global_coherence_avg', 1.0),
            global_data.get('global_satisfaction_avg', 50.0),
            global_data.get('territories_changed_hands', 0),
            global_data.get('units_created', 0),
            global_data.get('units_destroyed', 0),
            global_data.get('global_trade_volume', 0.0)
        ))

    def insert_trust_metrics(self, simulation_id: str, turn: int, trust_data: List[Dict[str, Any]]):
        """Batch inserts the trust matrix and relationship states."""
        if not trust_data:
            return
            
        insert_query = """
            INSERT INTO metrics_trust (
                simulation_id, turn, observer_id, target_id, trust_value, relationship_state
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        
        data = [
            (
                simulation_id,
                turn,
                row['observer_id'],
                row['target_id'],
                row.get('trust_value', 50.0),
                row.get('relationship_state', 'PEACE')
            )
            for row in trust_data
        ]
        
        self.conn.executemany(insert_query, data)

    def insert_action_outcomes(self, simulation_id: str, rows: List[Dict[str, Any]]):
        """Batch-inserts engine-level action outcomes for a turn."""
        if not rows:
            return

        query = """
            INSERT INTO metrics_action_outcomes
                (simulation_id, turn, nation_id, domain, action_type, status, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                simulation_id,
                r["turn"],
                r["nation_id"],
                r["domain"],
                r["action_type"],
                r["status"],
                r.get("reason"),
            )
            for r in rows
        ]
        self.conn.executemany(query, data)

    def insert_presidential_decisions(
        self, simulation_id: str, rows: List[Dict[str, Any]]
    ):
        """Batch-inserts presidential APPROVE/VETO decisions for a turn."""
        if not rows:
            return

        query = """
            INSERT INTO metrics_presidential_decisions
                (simulation_id, turn, nation_id, domain, decision, action_type, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                simulation_id,
                r["turn"],
                r["nation_id"],
                r["domain"],
                r["decision"],
                r.get("action_type"),
                r.get("reasoning"),
            )
            for r in rows
        ]
        self.conn.executemany(query, data)

    def close(self):
        """Closes the connection to DuckDB."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
