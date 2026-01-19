"""
Command-line interface for the rowing lineup setter.
"""

import json
import argparse
from typing import List
from pathlib import Path
from rower import Rower, Side, Experience, Boat
from simulated_annealing import LineupOptimizer
from multi_boat_optimizer import MultiBoatOptimizer


def load_rowers_from_json(filepath: str, convert_6k: bool = False) -> List[Rower]:
    """Load rowers from a JSON file"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    rowers = []
    for rower_data in data['rowers']:
        rowers.append(Rower.from_dict(rower_data, convert_6k=convert_6k))
    
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
        avg_attendance = sum(r.attendance_score for r in active_rowers) / len(active_rowers)
        print(f"Average Attendance Score: {avg_attendance:.1%}")
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


def print_multi_lineup_details(boats: List[List[Rower]], cost: float):
    """Print detailed information about multiple lineups."""
    print("\n" + "="*60)
    print(f"OPTIMAL MULTI-BOAT LINEUPS (Total Cost: {cost:.2f})")
    print("="*60)

    for i, lineup in enumerate(boats):
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
    parser.add_argument('--multi-boat', action='store_true',
                       help='Create multiple balanced boats instead of a single optimal one.')
    parser.add_argument('--convert-6k', action='store_true',
                       help='Convert 6k erg scores to estimated 2k scores.')
    
    args = parser.parse_args()
    
    # Load rowers from the specified data file
    rowers = load_rowers_from_json(args.data_file, convert_6k=args.convert_6k)
    
    if args.multi_boat:
        num_boats = len(rowers) // args.boat_type
        if num_boats == 0:
            print("Not enough rowers to create any boats.")
            return

        print(f"Optimizing for {num_boats} boats of {args.boat_type}...")
        
        best_lineups = None
        best_cost = float('inf')

        runs = args.runs if args.runs > 1 else 1
        for i in range(runs):

            optimizer = MultiBoatOptimizer(
                rowers=rowers,
                boat_type=args.boat_type,
                initial_temp=args.temp,
                cooling_rate=args.cooling
            )
            
            current_lineups, current_cost = optimizer.optimize()

            if runs > 1:
                print(f"--- Running multi-boat optimization {i+1}/{runs} Cost: {current_cost} ---")

            if current_cost < best_cost:
                best_lineups = current_lineups
                best_cost = current_cost

        print_multi_lineup_details(best_lineups, best_cost)
        
        # Update days_since_boated for all rowers
        if best_lineups:
            boated_rowers = {r.name for lineup in best_lineups for r in lineup}
            for rower in rowers:
                if rower.name in boated_rowers:
                    rower.days_since_boated = 0
                else:
                    rower.days_since_boated += 1
        
        save_rowers_to_json(rowers, args.data_file)

    else:
        best_lineup = None
        best_cost = float('inf')
        
        runs = args.runs if args.runs > 1 else 1
        
        for i in range(runs):   
            optimizer = LineupOptimizer(
                rowers=rowers,
                boat_type=args.boat_type,
                initial_temp=args.temp,
                cooling_rate=args.cooling,
                min_temp=1.0,
                iterations_per_temp=100
            )
            
            current_lineup, current_cost = optimizer.optimize()
            
            if runs > 1:
                print(f"--- Running multi-boat optimization {i+1}/{runs} Cost: {current_cost} ---")

            if current_cost < best_cost:
                best_lineup = current_lineup
                best_cost = current_cost
        
        # Create a boat and print details
        final_boat = Boat(args.boat_type)
        if best_lineup:
            for i, rower in enumerate(best_lineup):
                final_boat.assign_rower(i + 1, rower)
            
        print_lineup_details(final_boat, best_cost)
        
        # Update days_since_boated for all rowers
        if best_lineup:
            boated_rower_names = {r.name for r in best_lineup}
            for rower in rowers:
                if rower.name in boated_rower_names:
                    rower.days_since_boated = 0
                else:
                    rower.days_since_boated += 1
                    
        # Save updated rower data
        save_rowers_to_json(rowers, args.data_file)


if __name__ == "__main__":
    main()