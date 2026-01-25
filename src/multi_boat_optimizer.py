"""
Simulated annealing for optimizing multiple boat lineups.
"""

import random
import math
from typing import List, Tuple
from rower import Rower, Boat, Side, Experience
from optimizer import Optimizer

import yaml

class MultiBoatOptimizer(Optimizer):
    """
    Optimizes multiple boat lineups to be as evenly matched as possible.
    """

    def __init__(self, rowers: List[Rower], boat_type: int, config: dict = None, scoring_config: dict = None):
        super().__init__(rowers, scoring_config)
        self.boat_type = boat_type
        self.num_boats = len(rowers) // boat_type
        
        if not config:
            config = self._load_config()

        self.initial_temp = config.get('initial_temp', 1000.0)
        self.cooling_rate = config.get('cooling_rate', 0.95)
        self.min_temp = config.get('min_temp', 1.0)
        self.iterations_per_temp = config.get('iterations_per_temp', 100)

        if self.num_boats == 0:
            raise ValueError(f"Not enough rowers for a single boat of type {boat_type}.")

        self.best_solution = None
        self.best_cost = float('inf')

    def _load_config(self) -> dict:
        """Loads configuration from a YAML file."""
        try:
            with open('config.yaml', 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError):
            return {}

    def get_default_scoring_weights(self) -> dict:
        """Returns default scoring weights for multi-boat optimization."""
        return {
            'side_preference_penalty': 100.0,
            'experience_mixing_penalty': 1000.0,
            'inter_boat_variance_penalty': 100.0
        }

    def calculate_cost(self, boats: List[List[Rower]]) -> float:
        """
        Calculates the cost of a set of boat lineups.
        A lower cost indicates more evenly matched boats.
        """
        boat_costs = []
        avg_fitness_scores = []

        for boat_lineup in boats:
            if not boat_lineup:
                continue

            # Cost for individual boat (side preference, etc.)
            single_boat_cost = self.calculate_single_boat_cost(boat_lineup)
            boat_costs.append(single_boat_cost)

            # Average fitness for balancing
            avg_fitness = sum(r.fitness_score for r in boat_lineup) / len(boat_lineup)
            avg_fitness_scores.append(avg_fitness)

        # Cost from variance in average fitness scores between boats
        if len(avg_fitness_scores) > 1:
            mean_avg_fitness = sum(avg_fitness_scores) / len(avg_fitness_scores)
            variance = sum((s - mean_avg_fitness) ** 2 for s in avg_fitness_scores) / len(avg_fitness_scores)
        else:
            variance = 0

        # Total cost is the sum of individual boat costs plus the variance penalty
        total_cost = sum(boat_costs) + (variance * self.scoring_weights.get('inter_boat_variance_penalty', 100.0))
        return total_cost

    def calculate_single_boat_cost(self, lineup: List[Rower]) -> float:
        """Calculates the cost for a single boat."""
        cost = 0.0
        # Side preference mismatch penalty
        temp_boat = Boat(self.boat_type)
        for i, rower in enumerate(lineup):
            temp_boat.assign_rower(i + 1, rower)

        for seat in temp_boat.seats:
            if seat.rower and seat.rower.side_preference != Side.BOTH and seat.rower.side_preference != seat.side:
                cost += self.scoring_weights.get('side_preference_penalty', 100.0)

        # Experience mix penalty
        varsity_count = sum(1 for r in lineup if r.experience == Experience.VARSITY)
        if varsity_count > 0 and varsity_count < len(lineup):
            cost += self.scoring_weights.get('experience_mixing_penalty', 1000.0)  # Penalize mixed boats

        # Power distribution penalty (variance in fitness scores)
        avg_fitness = sum(r.fitness_score for r in lineup) / len(lineup)
        variance = sum((r.fitness_score - avg_fitness) ** 2 for r in lineup) / len(lineup)
        cost += variance * self.scoring_weights.get('power_variance_penalty', 0.1)

        # Stern-loading penalty (pairwise), align with single-boat logic
        for i in range(len(lineup) - 1):
            bow_rower = lineup[i]
            stern_rower = lineup[i + 1]
            if bow_rower.fitness_score < stern_rower.fitness_score:
                cost += (stern_rower.fitness_score - bow_rower.fitness_score) * \
                        self.scoring_weights.get('stern_loading_penalty', 15.0)

        return cost

    def generate_neighbor(self, current_boats: List[List[Rower]]) -> List[List[Rower]]:
        """
        Generates a neighbor solution by swapping two rowers between different boats.
        """
        neighbor = [list(b) for b in current_boats]
        
        # Choose two different boats to swap between
        boat_indices = list(range(len(neighbor)))
        if len(boat_indices) < 2:
            return neighbor # Not enough boats to swap

        b1_idx, b2_idx = random.sample(boat_indices, 2)
        
        # Choose a rower from each boat to swap
        r1_idx = random.randint(0, len(neighbor[b1_idx]) - 1)
        r2_idx = random.randint(0, len(neighbor[b2_idx]) - 1)

        # Swap the rowers
        neighbor[b1_idx][r1_idx], neighbor[b2_idx][r2_idx] = neighbor[b2_idx][r2_idx], neighbor[b1_idx][r1_idx]
        
        return neighbor

    def optimize(self) -> Tuple[List[List[Rower]], float]:
        """
        Runs the simulated annealing algorithm to find the best set of lineups.
        """
        # Initial state: randomly partition rowers into boats
        random.shuffle(self.rowers)
        initial_solution = []
        for i in range(self.num_boats):
            start = i * self.boat_type
            end = start + self.boat_type
            initial_solution.append(self.rowers[start:end])

        current_solution = initial_solution
        current_cost = self.calculate_cost(current_solution)
        
        self.best_solution = current_solution
        self.best_cost = current_cost
        
        temp = self.initial_temp

        while temp > self.min_temp:
            for _ in range(self.iterations_per_temp):
                neighbor = self.generate_neighbor(current_solution)
                neighbor_cost = self.calculate_cost(neighbor)
                
                cost_diff = neighbor_cost - current_cost
                
                if cost_diff < 0 or random.uniform(0, 1) < math.exp(-cost_diff / temp):
                    current_solution = neighbor
                    current_cost = neighbor_cost
                    
                    if current_cost < self.best_cost:
                        self.best_solution = current_solution
                        self.best_cost = current_cost
            
            temp *= self.cooling_rate
            
        return self.best_solution, self.best_cost

    def print_results(self):
        """Print detailed information about multiple lineups."""
        print("\n" + "="*60)
        print(f"OPTIMAL MULTI-BOAT LINEUPS (Total Cost: {self.best_cost:.2f})")
        print("="*60)

        if not self.best_solution:
            print("No solution found.")
            print("\n" + "="*60)
            return

        for i, lineup in enumerate(self.best_solution):
            boat_obj = Boat(len(lineup))
            for seat_idx, rower in enumerate(lineup):
                boat_obj.assign_rower(seat_idx + 1, rower)
            
            print(f"\n--- BOAT {i+1} ---")
            print(boat_obj)
            
            active_rowers = [r for r in lineup if r]
            if active_rowers:
                avg_erg = sum(r.erg_score for r in active_rowers) / len(active_rowers)
                minutes = int(avg_erg // 60)
                seconds = avg_erg % 60
                print(f"  Average Erg Score: {minutes}:{seconds:05.2f}")
                
                avg_attendance = sum(r.attendance_score for r in active_rowers) / len(active_rowers)
                print(f"  Average Attendance Score: {avg_attendance:.1%}")
                
                varsity_count = sum(1 for r in lineup if r and r.experience == Experience.VARSITY)
                novice_count = sum(1 for r in lineup if r and r.experience == Experience.NOVICE)
                print(f"  Experience: {varsity_count} Varsity, {novice_count} Novice")

        print("\n" + "="*60)
