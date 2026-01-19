"""
Command-line interface for the rowing lineup setter.
"""

import json
import argparse
from typing import List
from pathlib import Path
from rower import Rower, Side, Experience
from simulated_annealing import LineupOptimizer


def load_rowers_from_json(filepath: str) -> List[Rower]:
    """Load rowers from a JSON file"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    rowers = []
    for rower_data in data['rowers']:
        rowers.append(Rower.from_dict(rower_data))
    
    return rowers


def save_rowers_to_json(rowers: List[Rower], filepath: str):
    """Save rowers to a JSON file"""
    data = {
        'rowers': [rower.to_dict() for rower in rowers]
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def print_lineup_details(boat, cost: float):
    """Print detailed information about the lineup"""
    print("\n" + "="*60)
    print(f"OPTIMAL LINEUP (Cost: {cost:.2f})")
    print("="*60)
    print(boat)
    print("\n" + "-"*60)
    print("LINEUP STATISTICS")
    print("-"*60)
    
    lineup = boat.get_lineup()
    active_rowers = [r for r in lineup if r]
    
    # Average erg score
    if active_rowers:
        avg_erg = sum(r.erg_score for r in active_rowers) / len(active_rowers)
        minutes = int(avg_erg // 60)
        seconds = avg_erg % 60
        print(f"Average Erg Score: {minutes}:{seconds:05.2f}")
    
        # Average attendance
        avg_attendance = sum(r.attendance for r in active_rowers) / len(active_rowers)
        print(f"Average Attendance: {avg_attendance:.1%}")
    else:
        print("No rowers in lineup")
    
    # Experience breakdown
    varsity_count = sum(1 for r in lineup if r and r.experience == Experience.VARSITY)
    novice_count = sum(1 for r in lineup if r and r.experience == Experience.NOVICE)
    print(f"Experience: {varsity_count} Varsity, {novice_count} Novice")
    
    # Side preference match
    matches = 0
    for seat in boat.seats:
        if seat.rower:
            if seat.rower.side_preference == Side.BOTH or seat.rower.side_preference == seat.side:
                matches += 1
    print(f"Side Preference Matches: {matches}/{len(lineup)}")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Rowing Lineup Setter - Optimize boat lineups using simulated annealing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Optimize a boat of 8 from rowers.json
  python lineup_setter.py rowers.json --boat-type 8
  
  # Optimize a boat of 4 with custom parameters
  python lineup_setter.py rowers.json --boat-type 4 --temp 2000 --cooling 0.9
  
  # Run multiple optimizations to find best result
  python lineup_setter.py rowers.json --boat-type 8 --runs 5
        """
    )
    
    parser.add_argument('data_file', type=str,
                       help='JSON file containing rower data')
    parser.add_argument('--boat-type', type=int, choices=[4, 8], default=8,
                       help='Type of boat: 4 for fours, 8 for eights (default: 8)')
    parser.add_argument('--temp', type=float, default=1000.0,
                       help='Initial temperature for simulated annealing (default: 1000.0)')
    parser.add_argument('--cooling', type=float, default=0.95,
                       help='Cooling rate (default: 0.95)')
    parser.add_argument('--min-temp', type=float, default=1.0,
                       help='Minimum temperature (default: 1.0)')
    parser.add_argument('--iterations', type=int, default=100,
                       help='Iterations per temperature (default: 100)')
    parser.add_argument('--runs', type=int, default=1,
                       help='Number of optimization runs (returns best) (default: 1)')
    
    args = parser.parse_args()
    
    # Load rowers
    print(f"Loading rowers from {args.data_file}...")
    try:
        rowers = load_rowers_from_json(args.data_file)
        print(f"Loaded {len(rowers)} rowers")
    except FileNotFoundError:
        print(f"Error: File '{args.data_file}' not found")
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{args.data_file}': {e}")
        return 1
    except Exception as e:
        print(f"Error loading rowers: {e}")
        return 1
    
    # Check if we have enough rowers
    if len(rowers) < args.boat_type:
        print(f"Error: Not enough rowers for a {args.boat_type}. Need {args.boat_type}, have {len(rowers)}")
        return 1
    
    print(f"\nOptimizing lineup for a {args.boat_type}...")
    print(f"Running {args.runs} optimization(s)...\n")
    
    best_lineup = None
    best_cost = float('inf')
    best_boat = None
    
    # Run optimization multiple times if requested
    for run in range(args.runs):
        optimizer = LineupOptimizer(
            rowers=rowers,
            boat_type=args.boat_type,
            initial_temp=args.temp,
            cooling_rate=args.cooling,
            min_temp=args.min_temp,
            iterations_per_temp=args.iterations
        )
        
        lineup, cost = optimizer.optimize()
        
        if args.runs > 1:
            print(f"Run {run + 1}/{args.runs}: Cost = {cost:.2f}")
        
        if cost < best_cost:
            best_cost = cost
            best_lineup = lineup
            best_boat = optimizer.create_boat_with_lineup(lineup)
    
    # Print results
    print_lineup_details(best_boat, best_cost)
    
    return 0


if __name__ == '__main__':
    exit(main())
