#!/usr/bin/env python3
"""
Simulation Runner - Prototype Entry Point.

Quick prototype to run the GeoMAS simulation with configurable parameters.
Uses environment variables from .env for LLM configuration.

Usage:
    python run_simulation.py --turns 5 --nations 3 --cells 500 --seed 42
"""

import argparse
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load .env file if present
from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Run GeoMAS Simulation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Simulation parameters
    parser.add_argument("--turns", type=int, default=5,
                        help="Number of turns to simulate")
    parser.add_argument("--nations", type=int, default=6,
                        help="Number of nations (max 10)")
    parser.add_argument("--cells", type=int, default=800,
                        help="Number of map cells (provinces)")
    parser.add_argument("--map-seed", type=int, default=42, 
                        help="Seed for map generation")
    parser.add_argument("--history-seed", type=int, default=99, 
                        help="Seed for historical events")
    
    # Output options
    parser.add_argument("--db", type=str, default=None,
                        help="Path to save simulation database (optional)")
    parser.add_argument("--log", type=str, default=None,
                        help="Path to save simulation log file (optional)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print detailed logs")
    
    args = parser.parse_args()
    
    # Validate
    if args.nations > 10:
        print("⚠️  Maximum 10 nations supported. Using 10.")
        args.nations = 10
    if args.nations < 2:
        print("⚠️  Minimum 2 nations required. Using 2.")
        args.nations = 2
    
    # Auto-generate log file path if not specified
    if args.log is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.log = f"simulation_log_{timestamp}.json"
    
    # Print configuration
    print("=" * 60)
    print("🌍 GeoMAS SIMULATION RUNNER")
    print("=" * 60)
    print(f"📊 Turns:        {args.turns}")
    print(f"🏳️  Nations:      {args.nations}")
    print(f"🗺️  Cells:        {args.cells}")
    print(f"🎲 Map Seed:     {args.map_seed}")
    print(f"📜 History Seed: {args.history_seed}")
    print(f"🤖 Model:        {os.environ.get('AZURE_MODEL', 'Not set!')}")
    print(f"💾 Database:     {args.db or 'In-memory only'}")
    print(f"📝 Log File:     {args.log}")
    print("=" * 60)
    
    # Check LLM configuration
    if not os.environ.get("AZURE_API_KEY"):
        print("\n❌ ERROR: AZURE_API_KEY not set!")
        print("   Please configure your .env file with Azure credentials.")
        sys.exit(1)
    
    # Import simulation engine (after path setup)
    from geomas.simulation.engine import SimulationEngine
    from geomas.agents.llm_client import LLMClient
    
    # Initialize LLM client
    print("\n🔧 Initializing LLM Client...")
    client = LLMClient()
    print(f"   Using model: {client.model_name}")
    
    # Initialize simulation
    print("\n🌍 Generating World...")
    engine = SimulationEngine(
        map_seed=args.map_seed,
        history_seed=args.history_seed,
        n_cells=args.cells,
        llm_client=client,
        db_path=args.db
    )
    
    # Filter nations to requested count
    nation_ids = list(engine.world.nations.keys())[:args.nations]
    print(f"   Active nations: {nation_ids}")
    
    # Remove extra nations from world, agents, and matrices
    all_nation_ids = list(engine.world.nations.keys())
    for nid in all_nation_ids:
        if nid not in nation_ids:
            del engine.world.nations[nid]
            del engine.agents[nid]
            if nid in engine.opinion_agents:
                del engine.opinion_agents[nid]
    
    # Clean up trust matrix and relationship matrix
    for remaining_nid in nation_ids:
        if remaining_nid in engine.world.trust_matrix:
            engine.world.trust_matrix[remaining_nid] = {
                k: v for k, v in engine.world.trust_matrix[remaining_nid].items()
                if k in nation_ids
            }
        if remaining_nid in engine.world.relationship_matrix:
            engine.world.relationship_matrix[remaining_nid] = {
                k: v for k, v in engine.world.relationship_matrix[remaining_nid].items()
                if k in nation_ids
            }
    # Remove entries for deleted nations from matrices
    engine.world.trust_matrix = {
        k: v for k, v in engine.world.trust_matrix.items() if k in nation_ids
    }
    engine.world.relationship_matrix = {
        k: v for k, v in engine.world.relationship_matrix.items() if k in nation_ids
    }
    
    # Clean up map ownership (provinces)
    print("   Cleaning up map ownership...")
    count_cleared = 0
    for province in engine.world.provinces.values():
        if province.owner_id and province.owner_id not in nation_ids:
            province.owner_id = None
            count_cleared += 1
    print(f"   Cleared {count_cleared} provinces owned by removed nations.")

    # Clean up ContextManager (which was initialized with all nations)
    if hasattr(engine, 'context_manager') and engine.context_manager:
        cm = engine.context_manager
        print("   Cleaning up Context Manager...")
        
        # 1. Remove deleted nations from relationship_summaries (outer keys)
        cm.relationship_summaries = {
            k: v for k, v in cm.relationship_summaries.items() 
            if k in nation_ids
        }
        
        # 2. Remove deleted nations from relationship_summaries (inner keys)
        for nid in cm.relationship_summaries:
            cm.relationship_summaries[nid] = {
                k: v for k, v in cm.relationship_summaries[nid].items() 
                if k in nation_ids
            }
            
        # 3. Remove deleted nations from nation_actions
        cm.nation_actions = {
            k: v for k, v in cm.nation_actions.items() 
            if k in nation_ids
        }
        
        # 4. Remove deleted nations from _trust_history (outer keys)
        cm._trust_history = {
            k: v for k, v in cm._trust_history.items() 
            if k in nation_ids
        }
        
        # 5. Remove deleted nations from _trust_history (inner keys)
        for nid in cm._trust_history:
            cm._trust_history[nid] = {
                k: v for k, v in cm._trust_history[nid].items() 
                if k in nation_ids
            }

    # Prepare log data
    simulation_log = {
        "config": {
            "turns": args.turns,
            "nations": args.nations,
            "cells": args.cells,
            "map_seed": args.map_seed,
            "history_seed": args.history_seed,
            "model": client.model_name,
            "started_at": datetime.now().isoformat()
        },
        "initial_state": {},
        "turns": [],
        "final_state": {},
        "errors": []
    }
    
    # Log initial state
    for nid in nation_ids:
        nation = engine.world.nations[nid]
        simulation_log["initial_state"][nid] = {
            "name": nation.name,
            "population": nation.total_population,
            "budget": nation.total_budget,
            "food": nation.total_food,
            "energy": nation.total_energy,
            "materials": nation.total_materials
        }
    
    print(f"\n📊 Initial World State:")
    for nid in nation_ids:
        nation = engine.world.nations[nid]
        print(f"   {nation.name}: Pop={nation.total_population:,}, Budget={nation.total_budget:,.0f}")
    
    # Run simulation
    print(f"\n🚀 Starting simulation for {args.turns} turns...")
    print("=" * 60)
    
    for turn in range(args.turns):
        turn_start = engine.world.turn
        print(f"\n{'='*20} TURN {turn_start} {'='*20}")
        
        turn_data = {"turn": turn_start, "logs": [], "errors": []}
        
        try:
            engine.step()
            # Capture logs from this turn
            turn_data["logs"] = engine.turn_logs[-20:]  # Last 20 logs per turn
        except KeyboardInterrupt:
            print("\n\n⏹️  Simulation interrupted by user.")
            simulation_log["errors"].append({"turn": turn_start, "error": "User interrupt"})
            break
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ Error during turn {turn_start}: {error_msg}")
            turn_data["errors"].append(error_msg)
            simulation_log["errors"].append({"turn": turn_start, "error": error_msg})
            if args.verbose:
                import traceback
                traceback.print_exc()
            break
        
        simulation_log["turns"].append(turn_data)
    
    # Log final state
    for nid in nation_ids:
        if nid in engine.world.nations:
            nation = engine.world.nations[nid]
            simulation_log["final_state"][nid] = {
                "name": nation.name,
                "population": nation.total_population,
                "budget": nation.total_budget,
                "food": nation.total_food,
                "energy": nation.total_energy,
                "materials": nation.total_materials,
                "satisfaction": nation.public_satisfaction,
                "power": nation.power_projection
            }
    
    simulation_log["config"]["ended_at"] = datetime.now().isoformat()
    simulation_log["all_logs"] = engine.turn_logs
    
    # Save log file
    with open(args.log, "w") as f:
        json.dump(simulation_log, f, indent=2, default=str)
    print(f"\n📝 Log saved to: {args.log}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SIMULATION COMPLETE")
    print("=" * 60)
    print(f"   Turns completed: {engine.world.turn - 1}")
    
    for nid in nation_ids:
        if nid in engine.world.nations:
            nation = engine.world.nations[nid]
            print(f"\n   {nation.name}:")
            print(f"      Pop: {nation.total_population:,} | Budget: {nation.total_budget:,.0f}")
            print(f"      Food: {nation.total_food:,.0f} | Energy: {nation.total_energy:,.0f} | Materials: {nation.total_materials:,.0f}")
            print(f"      Satisfaction: {nation.public_satisfaction:.0f}/100 | Power: {nation.power_projection:,.1f}")
    
    if args.verbose:
        print("\n📜 Turn Logs:")
        for log in engine.turn_logs[-50:]:  # Last 50 logs
            print(f"   {log}")


if __name__ == "__main__":
    main()

