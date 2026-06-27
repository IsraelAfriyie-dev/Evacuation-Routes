"""Output module for exporting evacuation routes.

This module exports routes to CSV and GeoJSON formats
for use in GIS applications and analysis tools.
"""

import os
import json
import csv
import networkx as nx
import geopandas as gpd
from shapely.geometry import LineString, Point
from typing import List, Dict, Any, Optional

from routing import RouteResult


def export_route_to_csv(
    route: RouteResult,
    G: nx.MultiDiGraph,
    output_path: str = 'outputs/route.csv'
) -> str:
    """Export route segments to CSV file.
    
    Args:
        route: RouteResult containing the path
        G: NetworkX graph
        output_path: Path to save the CSV file
    
    Returns:
        Path to the saved CSV file
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'segment_id',
            'from_node',
            'to_node',
            'from_lat',
            'from_lon',
            'to_lat',
            'to_lon',
            'length_m',
            'length_km',
            'travel_time_sec',
            'travel_time_min',
            'speed_kmh',
            'highway_type',
            'road_name',
            'oneway'
        ])
        
        # Write each segment
        for i, (u, v, data) in enumerate(route.edges):
            from_lat = G.nodes[u]['y']
            from_lon = G.nodes[u]['x']
            to_lat = G.nodes[v]['y']
            to_lon = G.nodes[v]['x']
            
            writer.writerow([
                i + 1,
                u,
                v,
                from_lat,
                from_lon,
                to_lat,
                to_lon,
                data.get('length', 0),
                data.get('length', 0) / 1000,
                data.get('travel_time', 0),
                data.get('travel_time', 0) / 60,
                data.get('speed_kmh', 0),
                data.get('highway', 'unknown'),
                data.get('name', ''),
                data.get('oneway', False)
            ])
    
    print(f"Route CSV saved to {output_path}")
    return output_path


def export_route_to_geojson(
    route: RouteResult,
    G: nx.MultiDiGraph,
    output_path: str = 'outputs/route.geojson',
    include_network: bool = False,
    G_full: Optional[nx.MultiDiGraph] = None
) -> str:
    """Export route to GeoJSON file.
    
    Args:
        route: RouteResult containing the path
        G: NetworkX graph
        output_path: Path to save the GeoJSON file
        include_network: Whether to include full road network
        G_full: Full network graph if different from route graph
    
    Returns:
        Path to the saved GeoJSON file
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    features = []
    
    # Add route as LineString
    if route.path and len(route.path) > 1:
        route_coords = [[G.nodes[n]['x'], G.nodes[n]['y']] for n in route.path]  # GeoJSON is lon, lat
        
        route_feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': route_coords
            },
            'properties': {
                'type': 'route',
                'total_distance_m': route.total_distance,
                'total_distance_km': route.distance_km,
                'total_travel_time_sec': route.total_travel_time,
                'total_travel_time_min': route.travel_time_minutes,
                'node_count': len(route.path),
                'segment_count': len(route.edges)
            }
        }
        features.append(route_feature)
    
    # Add route segments as individual features
    for i, (u, v, data) in enumerate(route.edges):
        from_lat = G.nodes[u]['y']
        from_lon = G.nodes[u]['x']
        to_lat = G.nodes[v]['y']
        to_lon = G.nodes[v]['x']
        
        segment_feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': [[from_lon, from_lat], [to_lon, to_lat]]
            },
            'properties': {
                'type': 'segment',
                'segment_id': i + 1,
                'from_node': u,
                'to_node': v,
                'length_m': data.get('length', 0),
                'travel_time_sec': data.get('travel_time', 0),
                'speed_kmh': data.get('speed_kmh', 0),
                'highway_type': data.get('highway', 'unknown'),
                'road_name': data.get('name', ''),
                'oneway': data.get('oneway', False)
            }
        }
        features.append(segment_feature)
    
    # Add start and end points
    if route.path:
        start_node = route.path[0]
        end_node = route.path[-1]
        
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [G.nodes[start_node]['x'], G.nodes[start_node]['y']]
            },
            'properties': {
                'type': 'start_point',
                'node_id': start_node,
                'total_distance_km': route.distance_km,
                'total_travel_time_min': route.travel_time_minutes
            }
        })
        
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [G.nodes[end_node]['x'], G.nodes[end_node]['y']]
            },
            'properties': {
                'type': 'end_point',
                'node_id': end_node,
                'total_distance_km': route.distance_km,
                'total_travel_time_min': route.travel_time_minutes
            }
        })
    
    # Add full network if requested
    if include_network and G_full:
        for u, v, data in G_full.edges(data=True):
            if hasattr(G_full, 'edges'):
                try:
                    geom = G_full.edges[u, v, 0].get('geometry', None)
                    if geom:
                        coords = [[c[0], c[1]] for c in geom.coords]
                        features.append({
                            'type': 'Feature',
                            'geometry': {
                                'type': 'LineString',
                                'coordinates': coords
                            },
                            'properties': {
                                'type': 'network_edge',
                                'from_node': u,
                                'to_node': v,
                                'highway_type': data.get('highway', 'unknown'),
                                'length_m': data.get('length', 0)
                            }
                        })
                except:
                    pass
    
    # Create GeoJSON feature collection
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    # Save to file
    with open(output_path, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    print(f"Route GeoJSON saved to {output_path}")
    return output_path


def export_route_summary(
    route: RouteResult,
    G: nx.MultiDiGraph,
    output_path: str = 'outputs/route_summary.txt'
) -> str:
    """Export a text summary of the route.
    
    Args:
        route: RouteResult containing the path
        G: NetworkX graph
        output_path: Path to save the summary file
    
    Returns:
        Path to the saved summary file
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("EVACUATION ROUTE SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("ROUTE STATISTICS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total Distance: {route.distance_km:.2f} km\n")
        f.write(f"Total Travel Time: {route.travel_time_minutes:.1f} minutes\n")
        f.write(f"Number of Nodes: {len(route.path)}\n")
        f.write(f"Number of Segments: {len(route.edges)}\n\n")
        
        f.write("COORDINATES\n")
        f.write("-" * 40 + "\n")
        if route.path:
            start = route.path[0]
            end = route.path[-1]
            f.write(f"Start: ({G.nodes[start]['y']:.6f}, {G.nodes[start]['x']:.6f})\n")
            f.write(f"End: ({G.nodes[end]['y']:.6f}, {G.nodes[end]['x']:.6f})\n\n")
        
        f.write("SEGMENT BREAKDOWN\n")
        f.write("-" * 40 + "\n")
        
        # Group by highway type
        highway_stats = {}
        for u, v, data in route.edges:
            hw_type = data.get('highway', 'unknown')
            if hw_type not in highway_stats:
                highway_stats[hw_type] = {'count': 0, 'distance': 0, 'time': 0}
            highway_stats[hw_type]['count'] += 1
            highway_stats[hw_type]['distance'] += data.get('length', 0)
            highway_stats[hw_type]['time'] += data.get('travel_time', 0)
        
        for hw_type, stats in sorted(highway_stats.items()):
            f.write(f"\n{hw_type}:\n")
            f.write(f"  Segments: {stats['count']}\n")
            f.write(f"  Distance: {stats['distance']/1000:.2f} km\n")
            f.write(f"  Time: {stats['time']/60:.1f} min\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("END OF SUMMARY\n")
        f.write("=" * 60 + "\n")
    
    print(f"Route summary saved to {output_path}")
    return output_path


def export_all_formats(
    route: RouteResult,
    G: nx.MultiDiGraph,
    base_name: str = 'evacuation_route',
    output_dir: str = 'outputs'
) -> Dict[str, str]:
    """Export route in all supported formats.
    
    Args:
        route: RouteResult containing the path
        G: NetworkX graph
        base_name: Base name for output files
        output_dir: Output directory
    
    Returns:
        Dictionary mapping format to file path
    """
    os.makedirs(output_dir, exist_ok=True)
    
    outputs = {}
    
    # Export CSV
    csv_path = os.path.join(output_dir, f'{base_name}.csv')
    outputs['csv'] = export_route_to_csv(route, G, csv_path)
    
    # Export GeoJSON
    geojson_path = os.path.join(output_dir, f'{base_name}.geojson')
    outputs['geojson'] = export_route_to_geojson(route, G, geojson_path)
    
    # Export summary
    summary_path = os.path.join(output_dir, f'{base_name}_summary.txt')
    outputs['summary'] = export_route_summary(route, G, summary_path)
    
    return outputs


def create_route_gdf(
    route: RouteResult,
    G: nx.MultiDiGraph
) -> gpd.GeoDataFrame:
    """Create a GeoDataFrame from a route.
    
    Args:
        route: RouteResult containing the path
        G: NetworkX graph
    
    Returns:
        GeoDataFrame with route segments as features
    """
    features = []
    
    for i, (u, v, data) in enumerate(route.edges):
        from_lat = G.nodes[u]['y']
        from_lon = G.nodes[u]['x']
        to_lat = G.nodes[v]['y']
        to_lon = G.nodes[v]['x']
        
        geom = LineString([(from_lon, from_lat), (to_lon, to_lat)])
        
        features.append({
            'geometry': geom,
            'segment_id': i + 1,
            'from_node': u,
            'to_node': v,
            'length_m': data.get('length', 0),
            'travel_time_sec': data.get('travel_time', 0),
            'speed_kmh': data.get('speed_kmh', 0),
            'highway_type': data.get('highway', 'unknown'),
            'road_name': data.get('name', ''),
            'oneway': data.get('oneway', False)
        })
    
    return gpd.GeoDataFrame(features, crs='EPSG:4326')


if __name__ == '__main__':
    # Test output module
    import sys
    sys.path.insert(0, '.')
    
    from data_loader import load_or_download_network, get_node_nearest_to_point
    from routing import a_star_path
    
    print("Testing output module...")
    
    # Load network
    G = load_or_download_network(dist_km=5)
    
    # Find a test route
    source_point = (44.2601, -72.5754)
    target_point = (44.2200, -72.5800)
    
    source_node = get_node_nearest_to_point(G, source_point)
    target_node = get_node_nearest_to_point(G, target_point)
    
    route = a_star_path(G, source_node, target_node)
    
    if route:
        print(f"\nExporting route with {len(route.edges)} segments...")
        
        # Export all formats
        outputs = export_all_formats(route, G)
        
        print("\nExported files:")
        for fmt, path in outputs.items():
            print(f"  {fmt}: {path}")