# Montpelier Evacuation Route Planner

A Python-based evacuation route planner for Montpelier, Vermont using the A* shortest-path algorithm.

## Overview

This project implements an intelligent evacuation routing system that:
- Downloads and processes the road network for Montpelier, VT using OpenStreetMap data
- Uses the A* search algorithm with travel time as the edge cost
- Compares A* performance against Dijkstra's algorithm as a baseline
- Generates interactive and static route maps
- Exports routes to CSV and GeoJSON formats

## Algorithm

### A* Search Algorithm

The A* algorithm finds the shortest path by minimizing the total cost:

```
f(n) = g(n) + h(n)
```

Where:
- `g(n)` = actual cost from start to current node (travel time)
- `h(n)` = heuristic estimate from current node to goal (straight-line distance)

### Edge Cost Calculation

Travel time is computed as:
```
travel_time = road_length / road_speed_limit
```

Speed limits are derived from OSM data or estimated based on road type:
| Road Type | Default Speed (km/h) |
|-----------|---------------------|
| Motorway | 100 |
| Trunk | 80 |
| Primary | 65 |
| Secondary | 55 |
| Tertiary | 45 |
| Residential | 35 |
| Unclassified | 30 |

### Heuristic

The heuristic uses the Haversine formula to calculate straight-line distance:
```
h(n) = haversine(node_position, destination_position)
```

This ensures A* finds the optimal path while exploring fewer nodes than Dijkstra.

## Project Structure

```
Evacuation-Routes/
├── data/                    # Road network cache and GeoJSON exports
├── src/
│   ├── __init__.py
│   ├── data_loader.py       # OSM data fetching and processing
│   ├── routing.py           # A* and Dijkstra algorithms
│   ├── visualization.py     # Folium and Matplotlib maps
│   ├── output.py            # CSV and GeoJSON export
│   └── main.py              # CLI entry point
├── notebooks/
│   └── Evacuation_Route_Planner_Demo.ipynb
├── outputs/                 # Generated maps and route files
├── docs/                    # Documentation
├── requirements.txt
└── README.md
```

## Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/Evacuation-Routes.git
cd Evacuation-Routes

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
# Basic usage - find evacuation route
python src/main.py --source 44.2601,-72.5754 --dest 44.2200,-72.5800

# Compare A* with Dijkstra baseline
python src/main.py --source 44.2601,-72.5754 --dest 44.2200,-72.5800 --compare

# Export route to all formats (CSV, GeoJSON, summary)
python src/main.py --source 44.2601,-72.5754 --dest 44.2200,-72.5800 --export-all

# Use larger network coverage
python src/main.py --source 44.2601,-72.5754 --dest 44.2200,-72.5800 --dist-km 15

# Show full road network on map
python src/main.py --source 44.2601,-72.5754 --dest 44.2200,-72.5800 --show-network
```

### Python API

```python
from src.data_loader import load_or_download_network, get_node_nearest_to_point
from src.routing import a_star_path, dijkstra_path, compare_algorithms
from src.visualization import create_route_map
from src.output import export_all_formats

# Load road network
G = load_or_download_network(dist_km=10)

# Define points
source_point = (44.2601, -72.5754)
dest_point = (44.2200, -72.5800)

# Find nodes
source_node = get_node_nearest_to_point(G, source_point)
dest_node = get_node_nearest_to_point(G, dest_point)

# Find route using A*
route = a_star_path(G, source_node, dest_node)

# Display results
print(f"Distance: {route.distance_km:.2f} km")
print(f"Travel time: {route.travel_time_minutes:.1f} minutes")

# Create map
create_route_map(G, route, output_path='outputs/route_map.html')

# Export to all formats
export_all_formats(route, G, output_dir='outputs')

# Compare with Dijkstra
astar_result, dijkstra_result, metrics = compare_algorithms(G, source_node, dest_node)
```

## Output Files

| File | Description |
|------|-------------|
| `evacuation_route_map.html` | Interactive Folium map with route |
| `evacuation_route_static.png` | Static Matplotlib map |
| `route_comparison_map.html` | Comparison of A* and Dijkstra routes |
| `evacuation_route.csv` | Route segments as CSV |
| `evacuation_route.geojson` | Route as GeoJSON for GIS |
| `evacuation_route_summary.txt` | Text summary of route |

## Dependencies

- **osmnx**: Download and process OpenStreetMap road network data
- **networkx**: Graph data structures and pathfinding algorithms
- **geopandas**: Geospatial data handling
- **shapely**: Geometric operations
- **folium**: Interactive map visualization
- **matplotlib**: Static map generation
- **pandas**: Data analysis
- **numpy**: Numerical operations

## Algorithm Comparison

A* typically outperforms Dijkstra for finding single-source shortest paths because:

1. **Guided Search**: A* uses heuristic information to prioritize promising nodes
2. **Reduced Exploration**: Fewer nodes are visited compared to Dijkstra's blind search
3. **Optimality**: When the heuristic is admissible (never overestimates), A* finds the optimal path

For road networks with travel time as cost and straight-line distance as heuristic, A* provides significant speedup while guaranteeing optimal results.

## License

MIT License

## Contributing

Contributions welcome! Please create a pull request with your changes.