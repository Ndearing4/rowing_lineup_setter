"""
Simulated annealing for optimizing multiple boat lineups.
"""

import random
import math
from typing import List, Tuple
from rower import Rower, Boat, Side, Experience


class MultiBoatOptimizer:
    """
    Optimizes multiple boat lineups to be as evenly matched as possible.
    """

    def __init__(self, rowers: List[Rower], boat_type: int,
                 initial_temp: float = 1000.0,
                 cooling_rate: float = 0.95,
                 min_temp: float = 1.0,
                 iterations_per_temp: int = 100):
        self.rowers = rowers
        self.boat_type = boat_type
        self.num_boats = len(rowers) // boat_type
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.iterations_per_temp = iterations_per_temp

        if self.num_boats == 0:
            raise ValueError(f"Not enough rowers for a single boat of type {boat_type}.")

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
        total_cost = sum(boat_costs) + (variance * 100) # High penalty for imbalance
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
                cost += 100.0

        # Experience mix penalty
        varsity_count = sum(1 for r in lineup if r.experience == Experience.VARSITY)
        if varsity_count > 0 and varsity_count < len(lineup):
            cost += 1000.0  # Penalize mixed boats

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
        
        best_solution = current_solution
        best_cost = current_cost
        
        temp = self.initial_temp

        while temp > self.min_temp:
            for _ in range(self.iterations_per_temp):
                neighbor = self.generate_neighbor(current_solution)
                neighbor_cost = self.calculate_cost(neighbor)
                
                cost_diff = neighbor_cost - current_cost
                
                if cost_diff < 0 or random.uniform(0, 1) < math.exp(-cost_diff / temp):
                    current_solution = neighbor
                    current_cost = neighbor_cost
                    
                    if current_cost < best_cost:
                        best_solution = current_solution
                        best_cost = current_cost
            
            temp *= self.cooling_rate
            
        return best_solution, best_cost
