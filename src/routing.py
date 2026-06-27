"""Pathfinding algorithms for evacuation routing.

This module implements A* and Dijkstra shortest-path algorithms
using travel time as the edge cost.
"""

import numpy as np
import networkx as nx
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class RouteResult:
    """Container for route calculation results."""
    path: List[int]
    total_distance: float  # meters
    total_travel_time: float  # seconds
    edges: List[Tuple[int, int, Dict[str, Any]]]
    
    @property
    def distance_km(self) -> float:
        """Return distance in kilometers."""
        return self.total_distance / 1000
    
    @property
    def travel_time_minutes(self) -> float:
        """Return travel time in minutes."""
        return self.total_travel_time / 60
    
    @property
    def travel_time_hours(self) -> float:
        """Return travel time in hours."""
        return self.total_travel_time / 3600


def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """Calculate the great-circle distance between two points using Haversine formula.
    
    Args:
        lat1, lon1: Latitude and longitude of first point
        lat2, lon2: Latitude and longitude of second point
    
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)
    
    a = np.sin(delta_lat / 2) ** 2 + \
        np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c


def straight_line_heuristic(
    node: int,
    target: int,
    G: nx.MultiDiGraph
) -> float:
    """Calculate straight-line distance heuristic for A* algorithm.
    
    Args:
        node: Current node ID
        target: Target (destination) node ID
        G: NetworkX graph with node 'y' (lat) and 'x' (lon) attributes
    
    Returns:
        Estimated distance to target in meters (straight-line)
    """
    node_lat = G.nodes[node].get('y', 0)
    node_lon = G.nodes[node].get('x', 0)
    target_lat = G.nodes[target].get('y', 0)
    target_lon = G.nodes[target].get('x', 0)
    
    return haversine_distance(node_lat, node_lon, target_lat, target_lon)


def a_star_path(
    G: nx.MultiDiGraph,
    source: int,
    target: int,
    weight: str = 'travel_time'
) -> Optional[RouteResult]:
    """Find shortest path using A* algorithm with travel time costs.
    
    Args:
        G: NetworkX graph with travel_time edge attribute
        source: Source node ID
        target: Target node ID
        weight: Edge attribute to use as cost (default: 'travel_time')
    
    Returns:
        RouteResult object or None if no path exists
    """
    if source == target:
        return RouteResult(
            path=[source],
            total_distance=0,
            total_travel_time=0,
            edges=[]
        )
    
    try:
        # Use networkx astar_path with custom heuristic
        path = nx.astar_path(
            G,
            source,
            target,
            heuristic=lambda u, v: straight_line_heuristic(u, target, G) / 20,  # ~20 m/s max speed
            weight=weight
        )
        
        # Calculate total distance and travel time
        total_distance = 0.0
        total_travel_time = 0.0
        edges = []
        
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_data = G.edges[u, v, 0]
            total_distance += edge_data.get('length', 0)
            total_travel_time += edge_data.get('travel_time', 0)
            edges.append((u, v, edge_data))
        
        return RouteResult(
            path=path,
            total_distance=total_distance,
            total_travel_time=total_travel_time,
            edges=edges
        )
        
    except nx.NetworkXNoPath:
        print(f"No path found from {source} to {target}")
        return None
    except nx.NodeNotFound as e:
        print(f"Node not found: {e}")
        return None


def dijkstra_path(
    G: nx.MultiDiGraph,
    source: int,
    target: int,
    weight: str = 'travel_time'
) -> Optional[RouteResult]:
    """Find shortest path using Dijkstra's algorithm as baseline.
    
    Args:
        G: NetworkX graph with travel_time edge attribute
        source: Source node ID
        target: Target node ID
        weight: Edge attribute to use as cost (default: 'travel_time')
    
    Returns:
        RouteResult object or None if no path exists
    """
    if source == target:
        return RouteResult(
            path=[source],
            total_distance=0,
            total_travel_time=0,
            edges=[]
        )
    
    try:
        # Use networkx dijkstra_path
        path = nx.dijkstra_path(G, source, target, weight=weight)
        
        # Calculate total distance and travel time
        total_distance = 0.0
        total_travel_time = 0.0
        edges = []
        
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_data = G.edges[u, v, 0]
            total_distance += edge_data.get('length', 0)
            total_travel_time += edge_data.get('travel_time', 0)
            edges.append((u, v, edge_data))
        
        return RouteResult(
            path=path,
            total_distance=total_distance,
            total_travel_time=total_travel_time,
            edges=edges
        )
        
    except nx.NetworkXNoPath:
        print(f"No path found from {source} to {target}")
        return None
    except nx.NodeNotFound as e:
        print(f"Node not found: {e}")
        return None


def compare_algorithms(
    G: nx.MultiDiGraph,
    source: int,
    target: int
) -> Tuple[Optional[RouteResult], Optional[RouteResult], Dict[str, Any]]:
    """Compare A* and Dijkstra algorithms for the same source and target.
    
    Args:
        G: NetworkX graph with travel_time edge attribute
        source: Source node ID
        target: Target node ID
    
    Returns:
        Tuple of (A* result, Dijkstra result, comparison metrics)
    """
    import time
    
    # Run A*
    start_time = time.time()
    astar_result = a_star_path(G, source, target)
    astar_time = time.time() - start_time
    
    # Run Dijkstra
    start_time = time.time()
    dijkstra_result = dijkstra_path(G, source, target)
    dijkstra_time = time.time() - start_time
    
    # Calculate comparison metrics
    metrics = {
        'astar_time_sec': astar_time,
        'dijkstra_time_sec': dijkstra_time,
        'paths_equal': astar_result is not None and dijkstra_result is not None and
                       astar_result.path == dijkstra_result.path,
        'distance_difference_m': None,
        'time_difference_sec': None
    }
    
    if astar_result and dijkstra_result:
        metrics['distance_difference_m'] = abs(
            astar_result.total_distance - dijkstra_result.total_distance
        )
        metrics['time_difference_sec'] = abs(
            astar_result.total_travel_time - dijkstra_result.total_travel_time
        )
    
    return astar_result, dijkstra_result, metrics


def find_multiple_evacuation_routes(
    G: nx.MultiDiGraph,
    source: int,
    destinations: List[int],
    algorithm: str = 'astar'
) -> List[RouteResult]:
    """Find evacuation routes from a single source to multiple destinations.
    
    Args:
        G: NetworkX graph with travel_time edge attribute
        source: Source node ID
        destinations: List of destination node IDs
        algorithm: 'astar' or 'dijkstra'
    
    Returns:
        List of RouteResult objects for each destination
    """
    routing_func = a_star_path if algorithm == 'astar' else dijkstra_path
    
    routes = []
    for dest in destinations:
        result = routing_func(G, source, dest)
        if result:
            routes.append(result)
    
    return routes


def rank_destinations_by_travel_time(
    G: nx.MultiDiGraph,
    source: int,
    destinations: List[int],
    algorithm: str = 'astar'
) -> List[Tuple[int, RouteResult]]:
    """Rank destinations by shortest travel time from source.
    
    Args:
        G: NetworkX graph with travel_time edge attribute
        source: Source node ID
        destinations: List of destination node IDs
        algorithm: 'astar' or 'dijkstra'
    
    Returns:
        List of (destination_id, RouteResult) tuples sorted by travel time
    """
    routes = find_multiple_evacuation_routes(G, source, destinations, algorithm)
    
    # Sort by travel time
    ranked = [(r.edges[-1][1] if r.edges else dest, r) 
              for dest, r in zip(destinations, routes) if r]
    
    return sorted(ranked, key=lambda x: x[1].total_travel_time)


def get_route_segments(route: RouteResult) -> List[Dict[str, Any]]:
    """Extract route as a list of segment dictionaries.
    
    Args:
        route: RouteResult object
    
    Returns:
        List of segment dictionaries with geometry and attributes
    """
    segments = []
    
    for i, (u, v, data) in enumerate(route.edges):
        segment = {
            'segment_id': i + 1,
            'from_node': u,
            'to_node': v,
            'length_m': data.get('length', 0),
            'travel_time_sec': data.get('travel_time', 0),
            'speed_kmh': data.get('speed_kmh', 0),
            'highway_type': data.get('highway', 'unknown'),
            'name': data.get('name', 'unnamed'),
            'oneway': data.get('oneway', False)
        }
        segments.append(segment)
    
    return segments


if __name__ == '__main__':
    # Test the routing module
    from data_loader import load_or_download_network, get_node_nearest_to_point
    
    print("Testing routing algorithms...")
    
    # Load the network
    G = load_or_download_network(dist_km=5)
    
    # Define test points (downtown Montpelier to edge of coverage area)
    source_point = (44.2601, -72.5754)  # Montpelier center
    target_point = (44.2200, -72.5800)  # South of Montpelier
    
    source_node = get_node_nearest_to_point(G, source_point)
    target_node = get_node_nearest_to_point(G, target_point)
    
    print(f"\nSource node: {source_node} at {G.nodes[source_node]['y']}, {G.nodes[source_node]['x']}")
    print(f"Target node: {target_node} at {G.nodes[target_node]['y']}, {G.nodes[target_node]['x']}")
    
    # Compare algorithms
    astar_result, dijkstra_result, metrics = compare_algorithms(G, source_node, target_node)
    
    if astar_result:
        print(f"\nA* Route:")
        print(f"  Distance: {astar_result.distance_km:.2f} km")
        print(f"  Travel time: {astar_result.travel_time_minutes:.1f} minutes")
        print(f"  Path length: {len(astar_result.path)} nodes")
    
    if dijkstra_result:
        print(f"\nDijkstra Route:")
        print(f"  Distance: {dijkstra_result.distance_km:.2f} km")
        print(f"  Travel time: {dijkstra_result.travel_time_minutes:.1f} minutes")
        print(f"  Path length: {len(dijkstra_result.path)} nodes")
    
    print(f"\nComparison metrics:")
    print(f"  Paths equal: {metrics['paths_equal']}")
    print(f"  A* time: {metrics['astar_time_sec']*1000:.2f} ms")
    print(f"  Dijkstra time: {metrics['dijkstra_time_sec']*1000:.2f} ms")