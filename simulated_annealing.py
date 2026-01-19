"""
Simulated annealing algorithm for optimizing rowing lineups.
"""

import random
import math
from typing import List, Tuple
from rower import Rower, Boat, Side


class LineupOptimizer:
    """Optimizes boat lineups using simulated annealing"""
    
    def __init__(self, rowers: List[Rower], boat_type: int, 
                 initial_temp: float = 1000.0,
                 cooling_rate: float = 0.95,
                 min_temp: float = 1.0,
                 iterations_per_temp: int = 100):
        """
        Initialize the optimizer
        
        Args:
            rowers: List of available rowers
            boat_type: 4 or 8 for boat size
            initial_temp: Starting temperature for annealing
            cooling_rate: Rate at which temperature decreases
            min_temp: Minimum temperature before stopping
            iterations_per_temp: Number of iterations at each temperature
        """
        self.rowers = rowers
        self.boat_type = boat_type
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.iterations_per_temp = iterations_per_temp
        
        if len(rowers) < boat_type:
            raise ValueError(f"Not enough rowers for a {boat_type}: need {boat_type}, have {len(rowers)}")
    
    def calculate_cost(self, lineup: List[Rower]) -> float:
        """
        Calculate the cost (lower is better) of a lineup
        
        Considers:
        - Erg scores (faster is better)
        - Side preferences (matching preference is better)
        - Attendance (higher is better)
        - Balance between port and starboard
        """
        if len(lineup) != self.boat_type:
            return float('inf')
        
        boat = Boat(self.boat_type)
        for i, rower in enumerate(lineup):
            boat.assign_rower(i + 1, rower)
        
        cost = 0.0
        
        # Cost component 1: Total fitness (erg/attendance)
        for rower in lineup:
            cost += rower.fitness_score
        
        # Cost component 2: Side preference mismatch penalty
        side_penalty = 0.0
        for seat in boat.seats:
            if seat.rower:
                if seat.rower.side_preference != Side.BOTH:
                    if seat.rower.side_preference != seat.side:
                        # Penalty for being on non-preferred side
                        side_penalty += 100.0
        cost += side_penalty
        
        # Cost component 3: Experience balance
        # Prefer mixing novice and varsity rather than clustering
        varsity_count = sum(1 for r in lineup if r.experience.value == "varsity")
        # Ideal is balanced, so penalize extremes
        experience_imbalance = abs(varsity_count - len(lineup) / 2)
        cost += experience_imbalance * 10.0
        
        # Cost component 4: Power distribution
        # Calculate variance in fitness scores (prefer balanced power)
        avg_fitness = sum(r.fitness_score for r in lineup) / len(lineup)
        variance = sum((r.fitness_score - avg_fitness) ** 2 for r in lineup) / len(lineup)
        cost += variance * 0.1
        
        return cost
    
    def generate_neighbor(self, current: List[Rower]) -> List[Rower]:
        """Generate a neighbor solution by swapping two rowers"""
        neighbor = current.copy()
        i, j = random.sample(range(len(neighbor)), 2)
        neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
        return neighbor
    
    def optimize(self) -> Tuple[List[Rower], float]:
        """
        Run simulated annealing to find optimal lineup
        
        Returns:
            Tuple of (best_lineup, best_cost)
        """
        # Initialize with random lineup
        current = random.sample(self.rowers, self.boat_type)
        current_cost = self.calculate_cost(current)
        
        best = current.copy()
        best_cost = current_cost
        
        temperature = self.initial_temp
        
        while temperature > self.min_temp:
            for _ in range(self.iterations_per_temp):
                # Generate neighbor
                neighbor = self.generate_neighbor(current)
                neighbor_cost = self.calculate_cost(neighbor)
                
                # Calculate acceptance probability
                delta = neighbor_cost - current_cost
                
                if delta < 0:
                    # Better solution, always accept
                    accept = True
                else:
                    # Worse solution, accept with probability based on temperature
                    accept_prob = math.exp(-delta / temperature)
                    accept = random.random() < accept_prob
                
                if accept:
                    current = neighbor
                    current_cost = neighbor_cost
                    
                    # Update best if better
                    if current_cost < best_cost:
                        best = current.copy()
                        best_cost = current_cost
            
            # Cool down
            temperature *= self.cooling_rate
        
        return best, best_cost
    
    def create_boat_with_lineup(self, lineup: List[Rower]) -> Boat:
        """Create a boat object with the given lineup"""
        boat = Boat(self.boat_type)
        for i, rower in enumerate(lineup):
            boat.assign_rower(i + 1, rower)
        return boat
