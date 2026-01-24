from typing import Dict, List
from geomas.schemas.world import WorldState
from geomas.schemas.protocol import CountryEnvelope, GlobalStrategy
from geomas.world.map_engine import generate_world
from geomas.core.rules_engine import ActionEngine
from geomas.core import economy
from geomas.agents.nation_agent import NationAgent
from geomas.agents.llm_client import LLMClient


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
        
        # 0. ECONOMY PHASE (Update resources, collect taxes, apply consumption)
        self._economy_phase()
        
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
        import random
        random.shuffle(turn_envelopes)
        
        for envelope in turn_envelopes:
            logs = self.engine.execute_envelope(envelope)
            self.turn_logs.extend(logs)
            
        print(f"--- TURN {current_turn} COMPLETE ---")

    def _economy_phase(self):
        """
        Updates economic state for all nations at the start of each turn.
        
        1. Calculate aggregates from provinces
        2. Collect taxes
        3. Calculate production
        4. Calculate consumption
        5. Apply resource changes
        6. Handle deficits (starvation, energy penalties)
        7. Update power projection
        """
        for nation_id, nation in self.world.nations.items():
            # 1. Calculate aggregates
            aggregates = economy.calculate_nation_aggregates(nation, self.world)
            nation.total_population = aggregates["total_population"]
            nation.total_soldiers = aggregates["total_soldiers"]
            nation.total_aircraft = aggregates["total_aircraft"]
            nation.total_navy = aggregates["total_navy"]
            
            # 2. Collect taxes (adds to budget)
            tax_collected = economy.calculate_tax_collection(nation, self.world)
            nation.total_budget += tax_collected
            
            # 3. Add production to resource stockpiles
            nation.total_food += aggregates["total_food_production"]
            nation.total_energy += aggregates["total_energy_production"]
            nation.total_materials += aggregates["total_materials_production"]
            
            # 4. Calculate consumption
            food_consumed = economy.calculate_food_consumption(nation.total_population)
            energy_consumed = economy.calculate_energy_consumption(nation.total_population)
            materials_consumed = economy.calculate_materials_consumption(
                nation.total_soldiers,
                nation.total_aircraft,
                nation.total_navy
            )
            
            # 5. Apply consumption (subtract from stockpiles)
            nation.total_food -= food_consumed
            nation.total_energy -= energy_consumed
            nation.total_materials -= materials_consumed
            
            # 6. Handle deficits
            if nation.total_food < 0:
                casualties = economy.calculate_starvation_casualties(
                    nation.total_food,
                    nation.total_population
                )
                if casualties > 0:
                    self._apply_population_loss(nation_id, casualties)
                    self.turn_logs.append(
                        f"[CRISIS] {nation_id}: {casualties} died from starvation!"
                    )
                nation.total_food = 0  # Can't go negative
            
            if nation.total_energy < 0:
                penalty = economy.calculate_energy_penalty(nation.total_energy)
                self.turn_logs.append(
                    f"[CRISIS] {nation_id}: Energy shortage! Production penalty: {1 - penalty:.0%}"
                )
                # Apply penalty to next turn's production (stored in provinces)
                self._apply_production_penalty(nation_id, penalty)
                nation.total_energy = 0
            
            if nation.total_materials < 0:
                self.turn_logs.append(
                    f"[CRISIS] {nation_id}: Materials shortage! Military maintenance failing."
                )
                nation.total_materials = 0
            
            # 7. Update power projection
            nation.power_projection = economy.calculate_power_projection(nation)
            
            # Log economy summary
            self.turn_logs.append(
                f"[ECONOMY] {nation_id}: Budget={nation.total_budget:.0f}, "
                f"Food={nation.total_food:.0f}, Energy={nation.total_energy:.0f}, "
                f"Materials={nation.total_materials:.0f}, Power={nation.power_projection:.1f}"
            )

    def _apply_population_loss(self, nation_id: str, casualties: int):
        """
        Distributes population loss across provinces proportionally.
        """
        nation = self.world.nations[nation_id]
        total_pop = nation.total_population
        
        if total_pop == 0:
            return
        
        for p_id in nation.province_ids:
            province = self.world.provinces.get(p_id)
            if province and province.population > 0:
                # Proportional loss
                province_loss = int(casualties * (province.population / total_pop))
                province.population = max(0, province.population - province_loss)
                # Workers decrease proportionally
                province.workers = max(0, province.workers - province_loss)
                # Update tax revenue
                province.tax_revenue = province.population * 0.1

    def _apply_production_penalty(self, nation_id: str, penalty_multiplier: float):
        """
        Applies production penalty to all provinces of a nation.
        """
        nation = self.world.nations[nation_id]
        
        for p_id in nation.province_ids:
            province = self.world.provinces.get(p_id)
            if province:
                province.food_production *= penalty_multiplier
                province.energy_production *= penalty_multiplier
                province.materials_production *= penalty_multiplier

    def run(self, steps: int = 1):
        """Runs the simulation for N steps."""
        for _ in range(steps):
            self.step()
