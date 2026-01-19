# Rowing Lineup Setter

An intelligent application to help rowing coaches optimize boat lineups using simulated annealing algorithm.

## Features

- **Smart Optimization**: Uses simulated annealing to find optimal boat lineups
- **Multiple Factors**: Considers erg scores, side preferences, experience levels, and attendance
- **Flexible Boat Types**: Supports both 4s (fours) and 8s (eights)
- **JSON Data Storage**: Easy-to-edit JSON format for rower information
- **Command-Line Interface**: Simple CLI for quick lineup generation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Ndearing4/rowing_lineup_setter.git
cd rowing_lineup_setter
```

2. Install Python dependencies (Python 3.7+):
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Generate an optimal lineup for an 8:
```bash
python lineup_setter.py sample_rowers.json --boat-type 8
```

Generate an optimal lineup for a 4:
```bash
python lineup_setter.py sample_rowers.json --boat-type 4
```

### Advanced Usage

Run multiple optimizations and return the best result:
```bash
python lineup_setter.py sample_rowers.json --boat-type 8 --runs 5
```

Customize simulated annealing parameters:
```bash
python lineup_setter.py sample_rowers.json --boat-type 8 --temp 2000 --cooling 0.9 --iterations 200
```

### Command-Line Options

- `data_file`: Path to JSON file containing rower data (required)
- `--boat-type`: Type of boat - 4 or 8 (default: 8)
- `--temp`: Initial temperature for simulated annealing (default: 1000.0)
- `--cooling`: Cooling rate (default: 0.95)
- `--min-temp`: Minimum temperature before stopping (default: 1.0)
- `--iterations`: Iterations per temperature level (default: 100)
- `--runs`: Number of optimization runs, returns best (default: 1)

## Data Format

Rower data is stored in JSON format. Here's an example:

```json
{
  "rowers": [
    {
      "name": "Alice Johnson",
      "erg_score": 420.5,
      "side_preference": "port",
      "experience": "varsity",
      "attendance": 0.95
    },
    {
      "name": "Bob Smith",
      "erg_score": 425.2,
      "side_preference": "starboard",
      "experience": "varsity",
      "attendance": 0.92
    }
  ]
}
```

### Field Descriptions

- **name**: Rower's name (string)
- **erg_score**: 2000m erg time in seconds (float) - lower is better
- **side_preference**: Preferred rowing side - "port", "starboard", or "both" (string)
- **experience**: Experience level - "novice" or "varsity" (string)
- **attendance**: Attendance rate as decimal 0.0-1.0 (float)

## How It Works

The application uses **simulated annealing**, a probabilistic optimization algorithm that mimics the process of metal cooling. The algorithm:

1. Starts with a random lineup
2. Iteratively makes small changes (swapping rowers)
3. Accepts improvements and sometimes accepts worse solutions (to escape local optima)
4. Gradually "cools down", becoming more selective over time

### Cost Function

The optimizer considers multiple factors:

1. **Erg Scores**: Faster rowers are preferred, weighted by attendance
2. **Side Preferences**: Matching rowers to their preferred side
3. **Experience Balance**: Mixing novice and varsity rowers
4. **Power Distribution**: Balanced fitness across the boat

## Project Structure

```
rowing_lineup_setter/
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── lineup_setter.py           # Main CLI application
├── rower.py                   # Data models for rowers and boats
├── simulated_annealing.py     # Optimization algorithm
└── sample_rowers.json         # Example rower data
```

## Future Enhancements

- Web application interface
- Mobile app (iOS/Android)
- Multiple boat optimization
- Historical lineup tracking
- Performance analytics
- Cox assignment
- Lightweight/heavyweight categories

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.
