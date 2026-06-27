# Architecture Documentation

## System Overview

The Montpelier Evacuation Route Planner consists of several interconnected modules:

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Entry Point                          │
│                       (main.py)                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│                  (data_loader.py)                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ OSM Download    │  │ Cache Manager   │  │ Travel Time  │ │
│  │ (osmnx)         │  │ (pickle)        │  │ Calculator   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Graph Model                               │
│                 (networkx.MultiDiGraph)                      │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Nodes:          │  │ Edges:          │                   │
│  │ - id            │  │ - length        │                   │
│  │ - lat, lon      │  │ - travel_time   │                   │
│  │ - metadata      │  │ - speed_kmh     │                   │
│  └─────────────────┘  │ - highway_type  │                   │
│                       │ - name          │                   │
│                       └─────────────────┘                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Pathfinding Layer                            │
│                    (routing.py)                              │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ A* Algorithm    │  │ Dijkstra        │                   │
│  │ - heuristic     │  │ Algorithm       │                   │
│  │ - g(n) cost     │  │ - blind search  │                   │
│  │ - f(n) = g + h  │  │                 │                   │
│  └─────────────────┘  └─────────────────┘                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Visualization Layer                          │
│               (visualization.py)                             │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Folium Maps     │  │ Matplotlib      │                   │
│  │ (interactive)   │  │ (static)        │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Output Layer                               │
│                    (output.py)                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ CSV Export      │  │ GeoJSON Export  │  │ Text Summary │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Network Download**: osmnx downloads road network from OpenStreetMap
2. **Preprocessing**: Travel time calculated for each edge
3. **Caching**: Network saved to pickle file for fast loading
4. **Pathfinding**: A* or Dijkstra finds optimal route
5. **Visualization**: Route displayed on interactive or static maps
6. **Export**: Route data saved in various formats

## Key Data Structures

### RouteResult
```python
@dataclass
class RouteResult:
    path: List[int]              # Node IDs in order
    total_distance: float        # meters
    total_travel_time: float     # seconds
    edges: List[Tuple[int, int, Dict]]  # (u, v, data) tuples
```

### NetworkX Graph Attributes

**Node Attributes:**
- `y`: latitude
- `x`: longitude
- Additional OSM metadata

**Edge Attributes:**
- `length`: road length in meters
- `travel_time`: calculated travel time in seconds
- `speed_kmh`: speed limit in km/h
- `highway`: road type
- `name`: road name
- `oneway`: one-way flag
- `geometry`: LineString for curved roads

## Algorithm Details

### A* Implementation

```python
def a_star_path(G, source, target, weight='travel_time'):
    # Uses networkx.astar_path with custom heuristic
    path = nx.astar_path(
        G,
        source,
        target,
        heuristic=lambda u, v: straight_line_heuristic(u, target, G) / 20,
        weight=weight
    )
```

### Heuristic Function

Uses Haversine formula for great-circle distance:
```python
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    # ... calculation
    return R * c
```

### Edge Cost

Travel time = road_length / speed_limit
```python
travel_time = edge_length_m / (speed_kmh / 3.6)  # Convert to m/s
```

## Performance Considerations

1. **Network Caching**: Avoids re-downloading OSM data
2. **Heuristic Efficiency**: O(1) distance calculation
3. **Graph Representation**: MultiDiGraph handles parallel edges
4. **Memory**: Only route nodes/edges stored in RouteResult

## Extension Points

- Custom cost functions (traffic, weather)
- Multi-criteria optimization
- Dynamic re-routing
- Batch route planning