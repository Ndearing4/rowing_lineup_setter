"""
Simulated annealing algorithm for optimizing rowing lineups.
"""

import random
import math
import yaml
from typing import List, Tuple
from rower import Rower, Boat, Side
from optimizer import Optimizer


class LineupOptimizer(Optimizer):
    """Optimizes boat lineups using simulated annealing"""
    
    def __init__(self, rowers: List[Rower], boat_type: int, config: dict = None, scoring_config: dict = None):
        """
        Initialize the optimizer
        
        Args:
            rowers: List of available rowers
            boat_type: 4 or 8 for boat size
            config: Dictionary of simulated annealing parameters
            scoring_config: Dictionary of scoring weights
        """
        super().__init__(rowers, scoring_config)
        self.boat_type = boat_type
        
        if not config:
            config = self._load_config()

        self.initial_temp = config.get('initial_temp', 1000.0)
        self.cooling_schedule = config.get('cooling_schedule', 'exponential')
        self.cooling_rate = config.get('cooling_rate', 0.95)
        self.min_temp = config.get('min_temp', 1.0)
        self.iterations_per_temp = config.get('iterations_per_temp', 100)
        
        if len(rowers) < boat_type:
            raise ValueError(f"Not enough rowers for a {boat_type}: need {boat_type}, have {len(rowers)}")

        self.best_solution = None
        self.best_cost = float('inf')

    def _load_config(self) -> dict:
        """Loads configuration from a YAML file."""
        try:
            with open('config.yaml', 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError):
            return {}

    def get_default_scoring_weights(self):
        """Returns default scoring weights."""
        print("Using default scoring weights for LineupOptimizer.")
        return {
            'side_preference_penalty': 100.0,
            'experience_mixing_penalty': 10.0,
            'power_variance_penalty': 0.1,
            'stern_loading_penalty': 15.0,
            'days_since_boated_penalty': 5.0
        }
    
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
                        side_penalty += self.scoring_weights.get('side_preference_penalty', 100.0)
        cost += side_penalty
        
        # Cost component 3: Experience clustering
        # Prefer clustering novice and varsity rowers in separate boats
        from rower import Experience
        varsity_count = sum(1 for r in lineup if r.experience == Experience.VARSITY)
        novice_count = len(lineup) - varsity_count
        
        # Penalize mixed-experience boats. The penalty is lowest when one group is 0.
        # The penalty is highest when the boat is evenly split.
        experience_mixing_penalty = varsity_count * novice_count
        cost += experience_mixing_penalty * self.scoring_weights.get('experience_mixing_penalty', 10.0)
        
        # Cost component 4: Power distribution
        # Calculate variance in fitness scores (prefer balanced power)
        avg_fitness = sum(r.fitness_score for r in lineup) / len(lineup)
        variance = sum((r.fitness_score - avg_fitness) ** 2 for r in lineup) / len(lineup)
        cost += variance * self.scoring_weights.get('power_variance_penalty', 0.1)

        # Cost component 5: Stern-loading penalty (pairwise)
        # Penalize any rower who is stronger (lower fitness score) than the one behind them (closer to stern)
        for i in range(len(lineup) - 1):
            # i is closer to the bow, i+1 is closer to the stern
            bow_rower = lineup[i]
            stern_rower = lineup[i+1]
            if bow_rower.fitness_score < stern_rower.fitness_score:
                # The rower towards the bow is stronger than the one towards the stern, which is undesirable.
                # The penalty is proportional to the difference.
                cost += (stern_rower.fitness_score - bow_rower.fitness_score) * self.scoring_weights.get('stern_loading_penalty', 15.0)
        
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
        
        self.best_solution = current.copy()
        self.best_cost = current_cost
        
        temperature = self.initial_temp
        
        # For logarithmic cooling
        time_step = 0
        
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
                    if temperature > 0:
                        accept_prob = math.exp(-delta / temperature)
                        accept = random.random() < accept_prob
                    else:
                        accept = False
                
                if accept:
                    current = neighbor
                    current_cost = neighbor_cost
                    
                    # Update best if better
                    if current_cost < self.best_cost:
                        self.best_solution = current.copy()
                        self.best_cost = current_cost
            
            # Cool down
            time_step += 1
            if self.cooling_schedule == 'exponential':
                temperature *= self.cooling_rate
            elif self.cooling_schedule == 'linear':
                # Simple linear cooling
                # This might cool too fast or too slow depending on initial_temp and min_temp
                # A better linear schedule might depend on the total number of iterations
                num_steps = (self.initial_temp - self.min_temp) / (self.cooling_rate * 100) # a guess
                if num_steps > 0:
                    temperature -= self.cooling_rate
                else:
                    temperature = self.min_temp
            elif self.cooling_schedule == 'logarithmic':
                temperature = self.initial_temp / (1 + self.cooling_rate * math.log(1 + time_step))
            
            if temperature < self.min_temp:
                temperature = self.min_temp
        
        return self.best_solution, self.best_cost
    
    def create_boat_with_lineup(self, lineup: List[Rower]) -> Boat:
        """Create a boat object with the given lineup"""
        boat = Boat(self.boat_type)
        for i, rower in enumerate(lineup):
            boat.assign_rower(i + 1, rower)
        return boat
    
    def print_results(self):
        """Print the results of the optimization."""
        final_boat = Boat(self.boat_type)
        if self.best_solution:
            for i, rower in enumerate(self.best_solution):
                final_boat.assign_rower(i + 1, rower)
        
        print("\n" + "="*60)
        print(f"OPTIMAL LINEUP (Cost: {self.best_cost:.2f})")
        print("="*60)
        print(final_boat)
        print("\n" + "-"*60)
        print("LINEUP STATISTICS")
        print("-"*60)
        
        lineup = final_boat.get_lineup()
        active_rowers = [r for r in lineup if r]
        
        if active_rowers:
            avg_erg = sum(r.erg_score for r in active_rowers) / len(active_rowers)
            minutes = int(avg_erg // 60)
            seconds = avg_erg % 60
            print(f"Average Erg Score: {minutes}:{seconds:05.2f}")
        
            avg_attendance = sum(r.attendance_score for r in active_rowers) / len(active_rowers)
            print(f"Average Attendance Score: {avg_attendance:.1%}")
        else:
            print("No rowers in lineup")
        
        from rower import Experience
        varsity_count = sum(1 for r in lineup if r and r.experience == Experience.VARSITY)
        novice_count = sum(1 for r in lineup if r and r.experience == Experience.NOVICE)
        print(f"Experience: {varsity_count} Varsity, {novice_count} Novice")
        
        matches = 0
        for seat in final_boat.seats:
            if seat.rower:
                if seat.rower.side_preference == Side.BOTH or seat.rower.side_preference == seat.side:
                    matches += 1
        print(f"Side Preference Matches: {matches}/{len(lineup)}")
        print("="*60 + "\n")
