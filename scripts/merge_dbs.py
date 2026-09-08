#!/usr/bin/env python3
"""
merge_dbs.py — CLI script to merge multiple GeoMAS DuckDB databases into a single master.

Usage:
    # Merge all sims from source (including duplicates of baselines!)
    python scripts/merge_dbs.py \\
        --master data/simulation.duckdb \\
        --sources /path/to/copy_a/data/simulation.duckdb

    # Merge only NEW simulations (skip baselines already in master):
    python scripts/merge_dbs.py \\
        --master data/simulation.duckdb \\
        --sources /path/to/copy_a/data/simulation.duckdb \\
        --from-sim-id 4   # only sims with ID >= 4 in the source

    # Inspect what's inside a source DB before merging:
    python scripts/merge_dbs.py --list-sims /path/to/copy_a/data/simulation.duckdb

    # Or using pattern matching (glob):
    python scripts/merge_dbs.py \\
        --master data/simulation.duckdb \\
        --glob "/path/to/copies/*/data/simulation.duckdb" \\
        --from-sim-id 4

Notes:
    - Each source DB must have a corresponding <name>_metrics.duckdb in the same directory.
    - The master DB is updated IN PLACE. Backup it first if needed.
    - Use --from-sim-id to skip baseline simulations already present in the master.
    - Source DBs are NOT deleted unless --cleanup is specified.
"""
import argparse
import glob as glob_module
import os
import sys
from pathlib import Path


# Ensure the project root is on the path when run as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_source(raw: str, default_min_id: int) -> tuple:
    """
    Parse a source entry that may optionally carry a per-source min_id suffix.
    Supported formats:
      /path/to/simulation.duckdb        → uses default_min_id
      /path/to/simulation.duckdb:8      → uses min_id=8 for this source only
    Returns (resolved_path_str, min_id).
    """
    # Split on the LAST colon to avoid breaking Windows absolute paths
    if ":" in raw:
        # Try to parse the part after the last colon as an integer
        last_colon = raw.rfind(":")
        suffix = raw[last_colon + 1:]
        if suffix.isdigit():
            return str(Path(raw[:last_colon]).resolve()), int(suffix)
    return str(Path(raw).resolve()), default_min_id


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


def list_sims_in_db(db_path: str):
    """Print a table of simulations in a DB — useful for choosing --from-sim-id."""
    import duckdb
    if not validate_db(db_path):
        return
    with duckdb.connect(db_path, read_only=True) as conn:
        rows = conn.execute(
            "SELECT id, name, total_turns, created_at, scenario_json FROM simulation ORDER BY id"
        ).fetchall()
    print(f"\nSimulations in: {db_path}")
    print(f"{'ID':>4}  {'Name':<20}  {'Turns':>5}  {'Created At':<20}  Scenario")
    print("-" * 80)
    for r in rows:
        sim_id, name, turns, created_at, scenario_json = r
        scen = scenario_json[:40] if scenario_json else "—"
        print(f"{sim_id:>4}  {(name or '?'):<20}  {(turns or 0):>5}  {str(created_at):<20}  {scen}")
    print()


def do_merge(
    master_sim: str,
    master_metrics: str,
    sources: list,  # list of (path, min_id) tuples
    from_sim_id: int,  # global default, used when no per-source override
    cleanup: bool,
    dry_run: bool
):
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
    print(f"  From sim ID          : >= {from_sim_id}  (0 = all sims)")
    print(f"  Dry run              : {dry_run}")
    print(f"  Cleanup sources      : {cleanup}")
    print(f"{'='*60}\n")

    if not validate_db(master_sim):
        print("[ERROR] Master simulation DB is missing or empty. Aborting.")
        sys.exit(1)

    if dry_run:
        print("[DRY RUN] The following merges would be performed:")
        for i, (src, min_id) in enumerate(sources):
            metrics = resolve_metrics_path(src)
            print(f"  [{i + 1}] SIM:     {src}  ({'OK' if Path(src).exists() else 'MISSING'})")
            print(f"       METRICS: {metrics}  ({'OK' if Path(metrics).exists() else 'MISSING'})")
            print(f"       Min sim ID   : >= {min_id}")
            if min_id > 0 and Path(src).exists():
                # Show which sims would actually be included
                try:
                    import duckdb
                    with duckdb.connect(src, read_only=True) as c:
                        ids = [r[0] for r in c.execute("SELECT id FROM simulation ORDER BY id").fetchall()]
                    included = [x for x in ids if x >= min_id]
                    skipped = [x for x in ids if x < min_id]
                    print(f"       Include sims : {included}")
                    print(f"       Skip sims    : {skipped} (already in master)")
                except Exception:
                    pass
        print("\n[DRY RUN] No changes made.")
        return

    # Initialize merger with the master paths
    merger = DatabaseMerger(
        master_db_path=master_sim,
        master_metrics_path=master_metrics,
    )

    succeeded = 0
    failed = 0

    for i, (src, min_id) in enumerate(sources):
        print(f"[{i + 1}/{len(sources)}] Merging: {src}  (from sim_id >= {min_id})")

        if not validate_db(src):
            failed += 1
            continue

        metrics_path = resolve_metrics_path(src)
        print(f"          Metrics:  {metrics_path}")

        try:
            # Patch the merger to NOT auto-delete source files and respect from_sim_id
            actual_metrics = resolve_metrics_path(src)

            def _filtered_merge(worker_db_path: str, _min_id: int = min_id, _metrics: str = actual_metrics):
                """Merge only sims with id >= _min_id, without deleting sources."""
                import duckdb

                # --- Simulation DB ---
                id_mapping = {}
                with duckdb.connect(merger.master_db_path) as master_conn:
                    master_conn.execute(f"ATTACH '{worker_db_path}' AS worker")
                    res = master_conn.execute("SELECT MAX(id) FROM simulation").fetchone()
                    master_max_id = (res[0] or 0) if res else 0

                    worker_sims = master_conn.execute(
                        f"SELECT id FROM worker.simulation WHERE id >= {_min_id} ORDER BY id"
                    ).fetchall()

                    if not worker_sims:
                        print(f"          ⚠️  No sims with id >= {_min_id} found in source. Skipping.")
                        master_conn.execute("DETACH worker")
                        return {}

                    for (old_id,) in worker_sims:
                        new_id = old_id + master_max_id
                        id_mapping[old_id] = new_id
                        print(f"          Sim {old_id} → new Sim {new_id}")

                        # Explicit column lists prevent PK collisions on auto-increment `id`
                        master_conn.execute(f"""
                            INSERT INTO main.simulation
                                (id, uuid, genesis_seed, simulation_seed, n_cells, n_nations,
                                 created_at, completed_at, total_turns, name, scenario_json)
                            SELECT {new_id}, uuid, genesis_seed, simulation_seed, n_cells, n_nations,
                                   created_at, completed_at, total_turns, name, scenario_json
                            FROM worker.simulation WHERE id = {old_id}
                        """)
                        try:
                            master_conn.execute(f"""
                                INSERT INTO main.snapshots
                                    (simulation_id, turn, provinces_json, nations_json, trust_matrix,
                                     relationship_matrix, world_events_json, memory_json, created_at)
                                SELECT {new_id}, turn, provinces_json, nations_json, trust_matrix,
                                       relationship_matrix, world_events_json, memory_json, created_at
                                FROM worker.snapshots WHERE simulation_id = {old_id}
                            """)
                        except Exception as e:
                            print(f"          [WARN] snapshots: {e}")
                        try:
                            master_conn.execute(f"""
                                INSERT INTO main.envelopes
                                    (simulation_id, turn, nation_id, envelope_json, created_at)
                                SELECT {new_id}, turn, nation_id, envelope_json, created_at
                                FROM worker.envelopes WHERE simulation_id = {old_id}
                            """)
                        except Exception as e:
                            print(f"          [WARN] envelopes: {e}")
                        try:
                            master_conn.execute(f"""
                                INSERT INTO main.behaviors
                                    (simulation_id, turn, nation_id, deception_total, deception_defense,
                                     deception_foreign, coherence_score, global_strategy, government_type)
                                SELECT {new_id}, turn, nation_id, deception_total, deception_defense,
                                       deception_foreign, coherence_score, global_strategy, government_type
                                FROM worker.behaviors WHERE simulation_id = {old_id}
                            """)
                        except Exception as e:
                            print(f"          [WARN] behaviors: {e}")
                        try:
                            master_conn.execute(f"""
                                INSERT INTO main.token_usage
                                    (simulation_id, turn, nation_id, agent_type, prompt_tokens,
                                     completion_tokens, total_tokens, model, cost)
                                SELECT {new_id}, turn, nation_id, agent_type, prompt_tokens,
                                       completion_tokens, total_tokens, model, cost
                                FROM worker.token_usage WHERE simulation_id = {old_id}
                            """)
                        except Exception as e:
                            print(f"          [WARN] token_usage: {e}")
                    master_conn.execute("DETACH worker")

                # --- Metrics DB ---
                if id_mapping and os.path.exists(_metrics):
                    merger._merge_metrics_db(_metrics, id_mapping)

                return id_mapping

            result = _filtered_merge(src)

            if not result:
                failed += 1
                continue

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
    parser.add_argument(
        "--from-sim-id",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Only merge simulations with ID >= N from each source. "
            "Use this to skip baseline sims already present in the master "
            "(e.g. --from-sim-id 4 to skip Sims 1-3 that were already in the original project). "
            "Default 0 = merge all simulations."
        )
    )
    parser.add_argument(
        "--list-sims",
        nargs="*",
        metavar="PATH",
        help="List all simulations in one or more DB files (diagnostic, no merge performed)."
    )

    args = parser.parse_args()

    # --list-sims shortcut: just inspect and exit
    if args.list_sims is not None:
        paths = args.list_sims or [args.master]
        for p in paths:
            list_sims_in_db(str(Path(p).resolve()))
        sys.exit(0)

    # Resolve master paths
    master_sim = str(Path(args.master).resolve())
    master_metrics = (
        str(Path(args.master_metrics).resolve())
        if args.master_metrics
        else resolve_metrics_path(master_sim)
    )

    # Collect all sources — each entry may carry an optional :min_id suffix
    sources = [parse_source(p, args.from_sim_id) for p in args.sources]

    if args.glob:
        glob_matches = glob_module.glob(args.glob, recursive=True)
        sources += [parse_source(p, args.from_sim_id) for p in glob_matches]

    if not sources:
        print("[ERROR] No source databases specified. Use --sources or --glob.")
        print("        Run with --help for usage information.")
        sys.exit(1)

    # Remove the master from sources if accidentally included
    sources = [(s, m) for s, m in sources if s != master_sim]

    # Deduplicate while preserving order (key on path only)
    seen = set()
    unique_sources = []
    for s, m in sources:
        if s not in seen:
            seen.add(s)
            unique_sources.append((s, m))

    do_merge(master_sim, master_metrics, unique_sources, args.from_sim_id, args.cleanup, args.dry_run)


if __name__ == "__main__":
    main()
