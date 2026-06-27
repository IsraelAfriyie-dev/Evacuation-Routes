"""Road network data loader for Montpelier, Vermont evacuation planning.

This module handles downloading and loading the road network using osmnx,
and adds travel time attributes to edges based on road length and speed limits.
"""

import os
import networkx as nx
import osmnx as ox
from typing import Optional, Tuple
import pickle


# Default speed limits in km/h by road type (when not specified in OSM data)
DEFAULT_SPEEDS = {
    'motorway': 100,
    'trunk': 80,
    'primary': 65,
    'secondary': 55,
    'tertiary': 45,
    'residential': 35,
    'unclassified': 30,
    'service': 20,
    'pedestrian': 5,
    'track': 15,
    'path': 5,
    'default': 40  # km/h
}


def get_speed_kmh(edge_attrs: dict, highway_type: str) -> float:
    """Extract speed limit from edge attributes or use default.
    
    Args:
        edge_attrs: Dictionary of edge attributes from osmnx
        highway_type: The highway type string from OSM
    
    Returns:
        Speed limit in km/h
    """
    # Check for maxspeed tag
    maxspeed = edge_attrs.get('maxspeed', None)
    
    if maxspeed:
        # Handle various maxspeed formats
        if isinstance(maxspeed, (int, float)):
            speed = float(maxspeed)
        elif isinstance(maxspeed, str):
            # Remove 'km/h' or 'mph' suffixes and convert
            maxspeed_clean = maxspeed.lower().replace('km/h', '').replace('mph', '').strip()
            try:
                speed = float(maxspeed_clean)
                # Convert mph to km/h if needed
                if 'mph' in maxspeed.lower():
                    speed *= 1.60934
            except ValueError:
                speed = None
        else:
            speed = None
        
        if speed and speed > 0:
            return speed
    
    # Fall back to default based on highway type
    return DEFAULT_SPEEDS.get(highway_type, DEFAULT_SPEEDS['default'])


def download_montpelier_network(
    dist_km: float = 10,
    network_type: str = 'drive',
    custom_filter: Optional[str] = None
) -> nx.MultiDiGraph:
    """Download the road network for Montpelier, Vermont area.
    
    Args:
        dist_km: Distance in kilometers from city center to include
        network_type: Type of network ('drive', 'walk', 'bike', 'all')
        custom_filter: Custom OSM filter for roads to include
    
    Returns:
        NetworkX MultiDiGraph of the road network
    """
    # Montpelier, Vermont coordinates
    montpelier_center = (44.2601, -72.5754)
    
    print(f"Downloading road network for Montpelier, VT (radius: {dist_km} km)...")
    
    # Download the network
    if custom_filter:
        G = ox.graph_from_point(
            montpelier_center,
            dist=dist_km * 1000,  # Convert to meters
            network_type=network_type,
            custom_filter=custom_filter
        )
    else:
        G = ox.graph_from_point(
            montpelier_center,
            dist=dist_km * 1000,  # Convert to meters
            network_type=network_type
        )
    
    print(f"Downloaded network with {len(G.nodes)} nodes and {len(G.edges)} edges")
    
    return G


def add_travel_time_attributes(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Add travel time attributes to all edges in the graph.
    
    Travel time is calculated as: travel_time = road_length / road_speed
    
    Args:
        G: NetworkX graph with edge length attributes
    
    Returns:
        Graph with added 'travel_time' edge attribute (in seconds)
    """
    G = G.copy()
    
    for u, v, data in G.edges(data=True):
        # Get road length in meters
        length_m = data.get('length', 0)
        
        # Get highway type
        highway = data.get('highway', 'default')
        
        # Get speed limit
        speed_kmh = get_speed_kmh(data, highway)
        
        # Convert speed to m/s and calculate travel time
        speed_ms = speed_kmh / 3.6  # Convert km/h to m/s
        travel_time = length_m / speed_ms if speed_ms > 0 else float('inf')
        
        # Store travel time in seconds
        data['travel_time'] = travel_time
        data['speed_kmh'] = speed_kmh
        data['length_m'] = length_m
    
    return G


def load_or_download_network(
    cache_path: str = 'data/montpelier_network.pkl',
    dist_km: float = 10,
    force_download: bool = False
) -> nx.MultiDiGraph:
    """Load network from cache or download if not available.
    
    Args:
        cache_path: Path to save/load cached network
        dist_km: Distance from city center in kilometers
        force_download: Force download even if cache exists
    
    Returns:
        NetworkX MultiDiGraph with travel time attributes
    """
    os.makedirs(os.path.dirname(cache_path) if os.path.dirname(cache_path) else '.', exist_ok=True)
    
    if not force_download and os.path.exists(cache_path):
        print(f"Loading cached network from {cache_path}")
        with open(cache_path, 'rb') as f:
            G = pickle.load(f)
        print(f"Loaded network with {len(G.nodes)} nodes and {len(G.edges)} edges")
        return G
    
    # Download and process network
    G = download_montpelier_network(dist_km=dist_km)
    G = add_travel_time_attributes(G)
    
    # Save to cache
    print(f"Saving network to cache at {cache_path}")
    with open(cache_path, 'wb') as f:
        pickle.dump(G, f)
    
    return G


def get_node_nearest_to_point(G: nx.MultiDiGraph, point: Tuple[float, float]) -> int:
    """Find the nearest graph node to a given point.
    
    Args:
        G: NetworkX graph
        point: Tuple of (lat, lon)
    
    Returns:
        Node ID nearest to the point
    """
    return ox.distance.nearest_nodes(G, point[1], point[0])


def save_graph_as_geodataframe(
    G: nx.MultiDiGraph,
    nodes_path: str = 'data/nodes.geojson',
    edges_path: str = 'data/edges.geojson'
) -> Tuple[ox.elementify, ox.elementify]:
    """Save graph nodes and edges as GeoJSON files.
    
    Args:
        G: NetworkX graph
        nodes_path: Path to save nodes GeoJSON
        edges_path: Path to save edges GeoJSON
    
    Returns:
        Tuple of (nodes GeoDataFrame, edges GeoDataFrame)
    """
    gdf_nodes = ox.graph_to_gdfs(G, nodes=True, edges=False)
    gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(nodes_path) if os.path.dirname(nodes_path) else '.', exist_ok=True)
    os.makedirs(os.path.dirname(edges_path) if os.path.dirname(edges_path) else '.', exist_ok=True)
    
    # Save as GeoJSON
    gdf_nodes.to_file(nodes_path, driver='GeoJSON')
    gdf_edges.to_file(edges_path, driver='GeoJSON')
    
    print(f"Saved nodes to {nodes_path}")
    print(f"Saved edges to {edges_path}")
    
    return gdf_nodes, gdf_edges


if __name__ == '__main__':
    # Test the data loader
    print("Testing data loader...")
    G = load_or_download_network(dist_km=5)
    print(f"\nNetwork summary:")
    print(f"  Nodes: {len(G.nodes)}")
    print(f"  Edges: {len(G.edges)}")
    
    # Show sample edge attributes
    u, v, data = list(G.edges(data=True))[0]
    print(f"\nSample edge attributes (u={u}, v={v}):")
    for key, val in data.items():
        print(f"  {key}: {val}")