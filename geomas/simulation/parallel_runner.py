"""
Parallel Simulation Runner.

Enables concurrent execution of multiple simulations by using independent 
temporary databases for each process to bypass DuckDB write locking.
"""

import os
import shutil
import multiprocessing as mp
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from geomas.simulation.engine import SimulationEngine
from geomas.agents.llm_client import LLMClient
from geomas.db import SimulationDB

def worker_routine(
    worker_id: int, 
    n_turns: int, 
    map_seed: int, 
    history_seed: int, 
    n_cells: int, 
    n_nations: int,
    base_data_dir: str,
    planned_scenario: Optional[dict] = None,
    use_mock: bool = False
):
    """
    Routine executed by a single worker process.
    """
    # Use a unique DB for this worker
    worker_db = os.path.join(base_data_dir, f"worker_{worker_id}.duckdb")
    
    # Clean up if exists (should not happen if managed by ParallelBatchManager)
    if os.path.exists(worker_db):
        os.remove(worker_db)
        
    if use_mock:
        from web.mock_client import UIMockLLM
        client = UIMockLLM()
    else:
        client = LLMClient()
    
    # Initialize Engine
    sim = SimulationEngine(
        map_seed=map_seed,
        history_seed=history_seed,
        n_cells=n_cells,
        n_nations=n_nations,
        llm_client=client,
        db_path=worker_db,
        planned_scenario=planned_scenario
    )
    
    # Run for N turns
    for t in range(n_turns):
        sim.step()
        
    sim.close()
    return worker_db

class DatabaseMerger:
    """
    Handles merging of data from multiple worker databases into a master database.
    Performs ID remapping to ensure primary key integrity.
    """
    
    def __init__(self, master_db_path: str, master_metrics_path: str):
        self.master_db_path = master_db_path
        self.master_metrics_path = master_metrics_path

    def merge_worker(self, worker_db_path: str):
        """Merges a single worker DB into the master DBs."""
        worker_metrics_path = worker_db_path.replace(".duckdb", "_metrics.duckdb")
        
        # 1. Remap IDs and merge Simulation DB
        self._merge_simulation_db(worker_db_path)
        
        # 2. Remap IDs and merge Metrics DB
        self._merge_metrics_db(worker_metrics_path)
        
        # 3. Cleanup worker DBs
        if os.path.exists(worker_db_path):
            os.remove(worker_db_path)
        if os.path.exists(worker_metrics_path):
            os.remove(worker_metrics_path)

    def _merge_simulation_db(self, worker_db_path: str):
        import duckdb
        
        with duckdb.connect(self.master_db_path) as master_conn:
            # Attach worker DB
            master_conn.execute(f"ATTACH '{worker_db_path}' AS worker")
            
            # Find current max ID in master to offset
            res = master_conn.execute("SELECT MAX(id) FROM simulation").fetchone()
            offset = (res[0] or 0) if res else 0
            
            # Identify simulations in worker
            worker_sims = master_conn.execute("SELECT id FROM worker.simulation").fetchall()
            
            for (old_id,) in worker_sims:
                new_id = old_id + offset
                
                # Copy simulation metadata
                master_conn.execute(f"""
                    INSERT INTO main.simulation 
                    SELECT {new_id}, uuid, genesis_seed, simulation_seed, n_cells, n_nations, 
                           created_at, completed_at, total_turns, name, scenario_json 
                    FROM worker.simulation WHERE id = {old_id}
                """)
                
                # Copy Snapshots
                master_conn.execute(f"""
                    INSERT INTO main.snapshots 
                    SELECT {new_id}, turn, provinces_json, nations_json, trust_matrix, 
                           relationship_matrix, world_events_json, memory_json, created_at 
                    FROM worker.snapshots WHERE simulation_id = {old_id}
                """)
                
                # Copy Envelopes
                master_conn.execute(f"""
                    INSERT INTO main.envelopes 
                    SELECT {new_id}, turn, nation_id, envelope_json, created_at 
                    FROM worker.envelopes WHERE simulation_id = {old_id}
                """)
                
                # Copy Behaviors
                master_conn.execute(f"""
                    INSERT INTO main.behaviors 
                    SELECT {new_id}, turn, nation_id, deception_total, deception_defense, 
                           deception_foreign, coherence_score, global_strategy, government_type 
                    FROM worker.behaviors WHERE simulation_id = {old_id}
                """)
                
                # Copy Token Usage
                master_conn.execute(f"""
                    INSERT INTO main.token_usage 
                    SELECT {new_id}, turn, nation_id, agent_type, prompt_tokens, 
                           completion_tokens, total_tokens, model, cost 
                    FROM worker.token_usage WHERE simulation_id = {old_id}
                """)
                
            master_conn.execute("DETACH worker")

    def _merge_metrics_db(self, worker_metrics_path: str):
        if not os.path.exists(worker_metrics_path):
            return
            
        import duckdb
        with duckdb.connect(self.master_metrics_path) as master_conn:
            # Find offset again (same as above conceptually, but we need the actual IDs used in simulation table)
            # Actually, to be safe, we should map based on what we did in _merge_simulation_db.
            # Since workers start fresh (sim_id=1, 2...), the simple offset works perfectly if we match it.
            
            # We need to know the offset used in the Simulation DB to match.
            # But the Metrics DB itself might have a different max simulation_id if it's out of sync.
            # However, in GeoMAS, we always create they in pairs.
            
            # Let's get the mapping from the master Simulation DB (latest entries)
            # Or just pass the offset used.
            
            # For simplicity, we'll find the offset from the master Metrics DB
            # but this is only correct if no one else inserted anything in between.
            # The safest way is to know exactly which IDs were merged.
            
            # Since we only run this after merging simulation_id, we can look at the simulation table.
            # Wait, MetricsDB doesn't have a simulation table.
            
            # Let's just use the same logic: offset = max_sim_id in master_metrics
            res = master_conn.execute("SELECT MAX(simulation_id) FROM metrics_global").fetchone()
            # If metrics_global is empty, check other tables or fallback
            if not res or res[0] is None:
                res_n = master_conn.execute("SELECT MAX(simulation_id) FROM metrics_nation").fetchone()
                offset = (res_n[0] or 0) if res_n else 0
            else:
                offset = int(res[0])
            
            master_conn.execute(f"ATTACH '{worker_metrics_path}' AS worker")
            
            # Identify sims in worker (using metrics_global as proxy)
            worker_sims = master_conn.execute("SELECT DISTINCT simulation_id FROM worker.metrics_global").fetchall()
            
            for (old_id_raw,) in worker_sims:
                old_id = int(old_id_raw)
                new_id = old_id + offset
                
                # 1. Global Metrics
                master_conn.execute(f"""
                    INSERT INTO main.metrics_global 
                    (simulation_id, turn, global_deception_avg, global_coherence_avg, 
                     global_satisfaction_avg, territories_changed_hands, units_created, 
                     units_destroyed, global_trade_volume)
                    SELECT {new_id}, turn, global_deception_avg, global_coherence_avg, 
                           global_satisfaction_avg, territories_changed_hands, units_created, 
                           units_destroyed, global_trade_volume 
                    FROM worker.metrics_global WHERE simulation_id = {old_id}
                """)
                
                # 2. Nation Metrics
                master_conn.execute(f"""
                    INSERT INTO main.metrics_nation 
                    (simulation_id, turn, nation_id, deception_overall, deception_defense, 
                     deception_foreign, coherence_score, budget, food, energy, materials, 
                     population, workers, public_satisfaction, in_civil_unrest, 
                     soldiers, aircraft, navy, power_projection, trade_volume, military_spending)
                    SELECT {new_id}, turn, nation_id, deception_overall, deception_defense, 
                           deception_foreign, coherence_score, budget, food, energy, materials, 
                           population, workers, public_satisfaction, in_civil_unrest, 
                           soldiers, aircraft, navy, power_projection, trade_volume, military_spending 
                    FROM worker.metrics_nation WHERE simulation_id = {old_id}
                """)
                
                # 3. Trust Metrics
                master_conn.execute(f"""
                    INSERT INTO main.metrics_trust 
                    (simulation_id, turn, observer_id, target_id, trust_value, relationship_state)
                    SELECT {new_id}, turn, observer_id, target_id, trust_value, relationship_state 
                    FROM worker.metrics_trust WHERE simulation_id = {old_id}
                """)
                
                # 4. Action Outcomes
                master_conn.execute(f"""
                    INSERT INTO main.metrics_action_outcomes 
                    (simulation_id, turn, nation_id, domain, action_type, status, reason)
                    SELECT {new_id}, turn, nation_id, domain, action_type, status, reason 
                    FROM worker.metrics_action_outcomes WHERE simulation_id = {old_id}
                """)
                
                # 5. Presidential Decisions
                master_conn.execute(f"""
                    INSERT INTO main.metrics_presidential_decisions 
                    (simulation_id, turn, nation_id, domain, decision, action_type, reasoning)
                    SELECT {new_id}, turn, nation_id, domain, decision, action_type, reasoning 
                    FROM worker.metrics_presidential_decisions WHERE simulation_id = {old_id}
                """)
                
            master_conn.execute("DETACH worker")

class ParallelBatchManager:
    """
    Manages a batch of parallel simulations.
    """
    
    def __init__(self, n_workers: int = 3, data_dir: str = "data"):
        self.n_workers = n_workers
        self.data_dir = data_dir
        self.merger = DatabaseMerger(
            os.path.join(data_dir, "simulation.duckdb"),
            os.path.join(data_dir, "simulation_metrics.duckdb")
        )

    def run_batch(
        self, 
        n_turns: int, 
        map_seed: int, 
        history_seed: int, 
        n_cells: int, 
        n_nations: int,
        planned_scenario: Optional[dict] = None,
        progress_callback = None,
        use_mock: bool = False
    ):
        """
        Runs the batch in parallel.
        """
        processes = []
        pool = mp.Pool(processes=self.n_workers)
        
        results = []
        for i in range(self.n_workers):
            # All workers use the exact same seeds for 100% parity
            res = pool.apply_async(
                worker_routine,
                args=(
                    i, n_turns, map_seed, history_seed, n_cells, n_nations, 
                    self.data_dir, planned_scenario, use_mock
                )
            )
            results.append(res)
            
        # Monitor progress
        completed = 0
        total = self.n_workers
        worker_dbs = []
        
        while completed < total:
            new_completed = 0
            for r in results:
                if r.ready():
                    try:
                        r.wait(0) # Ensure it's done
                        new_completed += 1
                    except Exception as e:
                        pool.terminate()
                        pool.join()
                        raise RuntimeError(f"Worker failed with error: {e}")
            
            if new_completed > completed:
                completed = new_completed
                if progress_callback:
                    progress_callback(completed, total)
            time.sleep(1)
            
        # Collect DB paths
        for r in results:
            worker_dbs.append(r.get())
            
        pool.close()
        pool.join()
        
        # Merge
        if progress_callback:
            progress_callback(total, total, "Merging databases...")
            
        for db_path in worker_dbs:
            self.merger.merge_worker(db_path)
            
        if progress_callback:
            progress_callback(total, total, "Finished.")
            
        return True
