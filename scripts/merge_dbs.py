#!/usr/bin/env python3
"""
merge_dbs.py — CLI script to merge multiple GeoMAS DuckDB databases into a single master.

Usage:
    python scripts/merge_dbs.py \\
        --master data/simulation.duckdb \\
        --sources /path/to/copy_a/data/simulation.duckdb /path/to/copy_b/data/simulation.duckdb

    # Or using pattern matching (glob):
    python scripts/merge_dbs.py \\
        --master data/simulation.duckdb \\
        --glob "/path/to/copies/*/data/simulation.duckdb"

Notes:
    - Each source DB must have a corresponding <name>_metrics.duckdb in the same directory.
      (e.g. simulation.duckdb + simulation_metrics.duckdb)
    - The master DB is updated IN PLACE. Backup it first if needed.
    - Source DBs are NOT deleted (unlike in the parallel_runner worker flow). 
      Use --cleanup to delete them after a successful merge.
"""
import argparse
import glob as glob_module
import os
import sys
import shutil
from pathlib import Path


# Ensure the project root is on the path when run as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def resolve_metrics_path(sim_db_path: str) -> str:
    """
    Infer the metrics DB path from the simulation DB path.
    Tries both <name>_metrics.duckdb and simulation_metrics.duckdb conventions.
    """
    p = Path(sim_db_path)
    # Convention 1: same name + _metrics suffix  (e.g. simulation.duckdb → simulation_metrics.duckdb)
    candidate = p.parent / (p.stem + "_metrics" + p.suffix)
    if candidate.exists():
        return str(candidate)
    # Convention 2: fixed name in same directory
    candidate2 = p.parent / "simulation_metrics.duckdb"
    if candidate2.exists():
        return str(candidate2)
    return str(candidate)  # Return best guess even if missing (merger handles it gracefully)


def validate_db(path: str) -> bool:
    """Check that a DB file exists and has non-zero size."""
    p = Path(path)
    if not p.exists():
        print(f"  [SKIP] File not found: {path}")
        return False
    if p.stat().st_size == 0:
        print(f"  [SKIP] File is empty (0 bytes): {path}")
        return False
    return True


def do_merge(master_sim: str, master_metrics: str, sources: list[str], cleanup: bool, dry_run: bool):
    """
    Core merge logic. Iterates sources and merges each one into the master.
    """
    from geomas.simulation.parallel_runner import DatabaseMerger

    print(f"\n{'='*60}")
    print(f"  GeoMAS — Database Merge CLI")
    print(f"{'='*60}")
    print(f"  Master simulation DB : {master_sim}")
    print(f"  Master metrics DB    : {master_metrics}")
    print(f"  Total source DBs     : {len(sources)}")
    print(f"  Dry run              : {dry_run}")
    print(f"  Cleanup sources      : {cleanup}")
    print(f"{'='*60}\n")

    if not validate_db(master_sim):
        print("[ERROR] Master simulation DB is missing or empty. Aborting.")
        sys.exit(1)

    if dry_run:
        print("[DRY RUN] The following merges would be performed:")
        for i, src in enumerate(sources):
            metrics = resolve_metrics_path(src)
            print(f"  [{i + 1}] SIM:     {src}  ({'OK' if Path(src).exists() else 'MISSING'})")
            print(f"       METRICS: {metrics}  ({'OK' if Path(metrics).exists() else 'MISSING'})")
        print("\n[DRY RUN] No changes made.")
        return

    # Initialize merger with the master paths
    merger = DatabaseMerger(
        master_db_path=master_sim,
        master_metrics_path=master_metrics,
    )

    succeeded = 0
    failed = 0

    for i, src in enumerate(sources):
        print(f"[{i + 1}/{len(sources)}] Merging: {src}")

        if not validate_db(src):
            failed += 1
            continue

        metrics_path = resolve_metrics_path(src)
        print(f"          Metrics:  {metrics_path}")

        try:
            # Patch the merger to NOT auto-delete source files (unlike worker flow)
            # We do this by temporarily monkey-patching merge_worker to use
            # a custom non-destructive version.
            _original_merge_worker = merger.merge_worker

            def _non_destructive_merge_worker(worker_db_path: str):
                """Merge without deleting the source file afterwards."""
                worker_metrics_path = worker_db_path.replace(".duckdb", "_metrics.duckdb")
                # Infer correct metrics path
                actual_metrics = resolve_metrics_path(worker_db_path)
                id_mapping = merger._merge_simulation_db(worker_db_path)
                if id_mapping and os.path.exists(actual_metrics):
                    merger._merge_metrics_db(actual_metrics, id_mapping)
                # Do NOT delete sources here — cleanup is handled separately

            merger.merge_worker = _non_destructive_merge_worker
            merger.merge_worker(src)
            merger.merge_worker = _original_merge_worker

            print(f"          ✅ Done")
            succeeded += 1

            if cleanup:
                for f in [src, metrics_path]:
                    if os.path.exists(f):
                        os.remove(f)
                        print(f"          🗑️  Deleted: {f}")

        except Exception as e:
            print(f"          ❌ FAILED: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Merge complete — {succeeded} succeeded, {failed} failed")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Merge multiple GeoMAS DuckDB files into a single master database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--master",
        required=False,
        default="data/simulation.duckdb",
        help="Path to the master simulation.duckdb (default: data/simulation.duckdb)"
    )
    parser.add_argument(
        "--master-metrics",
        required=False,
        default=None,
        help="Path to the master metrics DB. Defaults to inferring from --master path."
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=[],
        metavar="PATH",
        help="One or more paths to source simulation.duckdb files to merge."
    )
    parser.add_argument(
        "--glob",
        default=None,
        metavar="PATTERN",
        help="Glob pattern to find source simulation.duckdb files (e.g. '*/data/simulation.duckdb')."
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        default=False,
        help="Delete source DB files after a successful merge."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be merged without making any changes."
    )

    args = parser.parse_args()

    # Resolve master paths
    master_sim = str(Path(args.master).resolve())
    master_metrics = (
        str(Path(args.master_metrics).resolve())
        if args.master_metrics
        else resolve_metrics_path(master_sim)
    )

    # Collect all sources
    sources = [str(Path(p).resolve()) for p in args.sources]

    if args.glob:
        glob_matches = glob_module.glob(args.glob, recursive=True)
        sources += [str(Path(p).resolve()) for p in glob_matches]

    if not sources:
        print("[ERROR] No source databases specified. Use --sources or --glob.")
        print("        Run with --help for usage information.")
        sys.exit(1)

    # Remove the master from sources if accidentally included
    sources = [s for s in sources if s != master_sim]

    # Deduplicate while preserving order
    seen = set()
    unique_sources = []
    for s in sources:
        if s not in seen:
            seen.add(s)
            unique_sources.append(s)

    do_merge(master_sim, master_metrics, unique_sources, args.cleanup, args.dry_run)


if __name__ == "__main__":
    main()
