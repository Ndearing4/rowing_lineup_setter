"""
Command-line interface for the rowing lineup setter.
"""

import json
import argparse
import yaml
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


def load_config(path: str) -> dict:
    """Load configuration from a YAML file."""
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return {}



def _handle_single_boat_results(best_lineup, best_cost, final_config, rowers):
    """Create boat, print details, and update rower data for a single boat."""
    final_boat = Boat(final_config['boat_type'])
    if best_lineup:
        for i, rower in enumerate(best_lineup):
            final_boat.assign_rower(i + 1, rower)
    
    print_lineup_details(final_boat, best_cost)
    
    if best_lineup:
        boated_rower_names = {r.name for r in best_lineup}
        for rower in rowers:
            if rower.name in boated_rower_names:
                rower.days_since_boated = 0
            else:
                rower.days_since_boated += 1
    
    save_rowers_to_json(rowers, final_config['data_file'])


def _handle_multi_boat_results(best_lineups, best_cost, final_config, rowers):
    """Print details and update rower data for multiple boats."""
    print_multi_lineup_details(best_lineups, best_cost)
    
    if best_lineups:
        boated_rowers = {r.name for lineup in best_lineups for r in lineup}
        for rower in rowers:
            if rower.name in boated_rowers:
                rower.days_since_boated = 0
            else:
                rower.days_since_boated += 1
    
    save_rowers_to_json(rowers, final_config['data_file'])


def main():
    # Load config from YAML file
    config_path = 'config.yaml'
    scoring_config_path = 'scoring_config.yaml'
    config = load_config(config_path)
    scoring_config = load_config(scoring_config_path)

    parser = argparse.ArgumentParser(
        description='Rowing Lineup Setter - Optimize boat lineups using simulated annealing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Optimize a boat of 8 from rowers.json
  python lineup_setter.py rowers.json --boat-type 8
  
  # Run multiple optimizations to find best result
  python lineup_setter.py rowers.json --boat-type 8 --runs 5

  # Create multiple balanced boats
  python lineup_setter.py rowers.json --multi-boat
        """
    )
    
    parser.add_argument('data_file', type=str, nargs='?', default=config.get('rower_data_file'),
                       help='JSON file containing rower data (overrides config.yaml)')
    parser.add_argument('--boat-type', type=int, choices=[4, 8],
                       help=f'Type of boat: 4 or 8 (default from config: {config.get("boat_type")})')
    parser.add_argument('--runs', type=int, default=config.get('runs', 1),
                       help='Number of optimization runs (returns best) (default from config: 1)')
    parser.add_argument('--multi-boat', action='store_true',
                       help='Create multiple balanced boats instead of a single optimal one.')
    parser.add_argument('--convert-6k', action='store_true',
                       help='Convert 6k erg scores to estimated 2k scores.')
    
    args = parser.parse_args()

    # Combine YAML config and CLI args
    final_config = config.copy()
    cli_args = {k: v for k, v in vars(args).items() if v is not None}
    final_config.update(cli_args)
    
    if not final_config.get('data_file'):
        parser.error("the following arguments are required: data_file (or set 'rower_data_file' in config.yaml)")

    # Load rowers from the specified data file
    rowers = load_rowers_from_json(final_config['data_file'], convert_6k=final_config.get('convert_6k', False))
    
    # Determine which optimizer to use
    if final_config.get('multi_boat'):
        optimizer_class = MultiBoatOptimizer
        num_boats = len(rowers) // final_config['boat_type']
        if num_boats == 0:
            print("Not enough rowers to create any boats.")
            return
        print(f"Optimizing for {num_boats} boats of {final_config['boat_type']}...")
    else:
        optimizer_class = LineupOptimizer

    best_result = None
    best_cost = float('inf')
    
    runs = final_config.get('runs', 1)
    
    for i in range(runs):
        optimizer = optimizer_class(
            rowers=rowers,
            boat_type=final_config['boat_type'],
            config=final_config,
            scoring_config=scoring_config
        )
        
        current_result, current_cost = optimizer.optimize()
        
        if runs > 1:
            print(f"--- Running optimization {i+1}/{runs} Cost: {current_cost} ---")

        if current_cost < best_cost:
            best_result = current_result
            best_cost = current_cost
    
    # Handle results

    optimizer.print_results()

    # if final_config.get('multi_boat'):
    #     _handle_multi_boat_results(best_result, best_cost, final_config, rowers)
    # else:
    #     _handle_single_boat_results(best_result, best_cost, final_config, rowers)


if __name__ == "__main__":
    main()