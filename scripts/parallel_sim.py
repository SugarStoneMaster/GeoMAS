#!/usr/bin/env python3
"""
Parallel Simulation CLI Runner.

Usage:
    python3 scripts/parallel_sim.py --turns 50 --workers 3 --map-seed 42
"""

import argparse
import os
import sys

# Path fix for local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from geomas.simulation.parallel_runner import ParallelBatchManager

def main():
    parser = argparse.ArgumentParser(description="GeoMAS Parallel Simulation Runner")
    parser.add_argument("--turns", type=int, default=10, help="Number of turns to run per simulation")
    parser.add_argument("--workers", type=int, default=3, help="Number of parallel instances")
    parser.add_argument("--map-seed", type=int, default=42, help="Seed for map generation")
    parser.add_argument("--hist-seed", type=int, default=99, help="Base seed for history/simulation")
    parser.add_argument("--cells", type=int, default=300, help="Number of cells in the Voronoi map")
    parser.add_argument("--nations", type=int, default=4, help="Number of nations")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory for database files")
    parser.add_argument("--dry-run", action="store_true", help="Use mock LLM (no API calls)")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting {args.workers} parallel simulations {'(DRY RUN)' if args.dry_run else ''}...")
    print(f"📈 Configuration: {args.turns} turns, Seed {args.map_seed}, {args.nations} nations")
    
    manager = ParallelBatchManager(n_workers=args.workers, data_dir=args.data_dir)
    
    def cli_progress(current, total, msg=None):
        if msg:
            print(f"🔄 {msg}")
        else:
            print(f"✅ Instance {current}/{total} finished.")
            
    try:
        manager.run_batch(
            n_turns=args.turns,
            map_seed=args.map_seed,
            history_seed=args.hist_seed,
            n_cells=args.cells,
            n_nations=args.nations,
            progress_callback=cli_progress,
            use_mock=args.dry_run
        )
        print("\n✨ Batch completed successfully and merged into master database.")
    except Exception as e:
        print(f"\n❌ Error during parallel execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
