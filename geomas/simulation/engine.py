"""
Simulation Engine.

The Main Loop. Orchestrates the flow of time, agent decisions, and world updates.
"""

import random
from typing import Dict, List
from geomas.agents.schemas import CountryEnvelope, GlobalStrategy
from geomas.world import generate_world
from geomas.actions import ActionEngine
from geomas.agents.nation_agent import NationAgent
from geomas.agents.llm_client import LLMClient
from geomas.simulation.phases import run_upkeep_phase


class SimulationEngine:
    """
    The Main Loop. Orchestrates the flow of time, agent decisions, and world updates.
    """

    def __init__(self, map_seed: int = 42, history_seed: int = 99, n_cells: int = 1500, llm_client: LLMClient = None):
        # 1. Initialize World
        self.world = generate_world(seed=map_seed, history_seed=history_seed, n_cells=n_cells)
        
        # 2. Initialize Engine
        self.engine = ActionEngine(self.world)
        
        # 3. Initialize Agents
        self.agents: Dict[str, NationAgent] = {}
        self.client = llm_client or LLMClient() 
        
        self._init_agents()
        
        # Simulation State
        self.turn_logs: List[str] = []
        # Store full envelopes for rich history visualization
        # List of turns, where each turn is a list of envelopes
        self.history: List[List[CountryEnvelope]] = [] 

    def _init_agents(self):
        """Creates a NationAgent for each nation in the world."""
        for nation_id in self.world.nations:
            strategy = GlobalStrategy.COALITION_BUILDER 
            
            self.agents[nation_id] = NationAgent(
                nation_id=nation_id,
                world=self.world,
                llm_client=self.client,
                global_strategy=strategy
            )

    def step(self):
        """Executes one full turn of the simulation."""
        # Increment Turn FIRST
        self.world.turn += 1
        current_turn = self.world.turn
        
        print(f"--- STARTING TURN {current_turn} ---")
        self.turn_logs.append(f"--- TURN {current_turn} ---")
        
        # 0. UPKEEP PHASE (resources, consumption, crisis)
        run_upkeep_phase(self.world, self.turn_logs)
        
        turn_envelopes: List[CountryEnvelope] = []
        
        # 1. AGENT PHASE (Decision)
        for agent_id, agent in self.agents.items():
            print(f"Agent {agent_id} is thinking...")
            try:
                envelope = agent.act(current_turn)
                turn_envelopes.append(envelope)
            except Exception as e:
                print(f"Error agent {agent_id}: {e}")
        
        # Store envelopes in history
        self.history.append(turn_envelopes)
        
        # 2. EXECUTION PHASE (Action)
        random.shuffle(turn_envelopes)
        
        for envelope in turn_envelopes:
            logs = self.engine.execute_envelope(envelope)
            self.turn_logs.extend(logs)
            
        print(f"--- TURN {current_turn} COMPLETE ---")

    def run(self, steps: int = 1):
        """Runs the simulation for N steps."""
        for _ in range(steps):
            self.step()
