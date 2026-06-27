#!/usr/bin/env python3
"""Main entry point for the Montpelier Evacuation Route Planner.

This script provides a CLI interface for:
- Loading the Montpelier, VT road network
- Finding optimal evacuation routes using A* algorithm
- Comparing with Dijkstra baseline
- Visualizing routes on interactive maps
- Exporting routes to CSV/GeoJSON
"""

import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_or_download_network, get_node_nearest_to_point
from routing import a_star_path, dijkstra_path, compare_algorithms, RouteResult
from visualization import (
    create_route_map, create_comparison_map, 
    create_static_route_map, create_multi_route_map
)
from output import export_all_formats


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Montpelier Evacuation Route Planner - A* Pathfinding',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find evacuation route from downtown to south of city
  python src/main.py --source 44.2601,-72.5754 --dest 44.2200,-72.5800

  # Compare A* with Dijkstra and save comparison map
  python src/main.py --source 44.2601,-72.5754 --dest 44.2200,-72.5800 --compare

  # Use larger network coverage and save all outputs
  python src/main.py --source 44.2601,-72.5754 --dest 44.2200,-72.5800 \\
      --dist-km 15 --export-all --output-dir outputs
        """
    )
    
    parser.add_argument(
        '--source', '-s',
        type=str,
        required=True,
        help='Source coordinates as lat,lon (e.g., "44.2601,-72.5754")'
    )
    
    parser.add_argument(
        '--dest', '-d',
        type=str,
        required=True,
        help='Destination coordinates as lat,lon (e.g., "44.2200,-72.5800")'
    )
    
    parser.add_argument(
        '--dist-km',
        type=float,
        default=10,
        help='Network coverage radius in km (default: 10)'
    )
    
    parser.add_argument(
        '--algorithm',
        choices=['astar', 'dijkstra', 'both'],
        default='astar',
        help='Algorithm to use (default: astar)'
    )
    
    parser.add_argument(
        '--compare',
        action='store_true',
        help='Compare A* with Dijkstra baseline'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs',
        help='Output directory for files (default: outputs)'
    )
    
    parser.add_argument(
        '--export-all',
        action='store_true',
        help='Export route in all formats (CSV, GeoJSON, summary)'
    )
    
    parser.add_argument(
        '--show-network',
        action='store_true',
        help='Show full road network on map (slower)'
    )
    
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Force re-download of road network'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-essential output'
    )
    
    return parser.parse_args()


def parse_coords(coord_str: str) -> tuple:
    """Parse coordinate string to tuple."""
    try:
        parts = coord_str.split(',')
        if len(parts) != 2:
            raise ValueError("Coordinates must be lat,lon format")
        return (float(parts[0]), float(parts[1]))
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid coordinates: {coord_str}. Use lat,lon format.")


def print_route_info(route: RouteResult, label: str = "Route"):
    """Print route information."""
    print(f"\n{label}:")
    print(f"  Distance: {route.distance_km:.2f} km ({route.total_distance:.0f} m)")
    print(f"  Travel Time: {route.travel_time_minutes:.1f} minutes ({route.total_travel_time:.0f} seconds)")
    print(f"  Nodes: {len(route.path)}")
    print(f"  Segments: {len(route.edges)}")


def main():
    """Main function."""
    args = parse_args()
    
    # Parse coordinates
    source_point = parse_coords(args.source)
    dest_point = parse_coords(args.dest)
    
    if not args.quiet:
        print("=" * 60)
        print("MONTPELIER EVACUATION ROUTE PLANNER")
        print("A* Shortest Path Algorithm")
        print("=" * 60)
        print(f"\nSource: {source_point[0]:.6f}, {source_point[1]:.6f}")
        print(f"Destination: {dest_point[0]:.6f}, {dest_point[1]:.6f}")
        print(f"Network coverage: {args.dist_km} km")
    
    # Load network
    cache_path = f'data/montpelier_network_{int(args.dist_km)}km.pkl'
    G = load_or_download_network(
        cache_path=cache_path,
        dist_km=args.dist_km,
        force_download=args.no_cache
    )
    
    # Find nearest nodes
    source_node = get_node_nearest_to_point(G, source_point)
    dest_node = get_node_nearest_to_point(G, dest_point)
    
    if not args.quiet:
        print(f"\nSource node: {source_node} at ({G.nodes[source_node]['y']:.6f}, {G.nodes[source_node]['x']:.6f})")
        print(f"Destination node: {dest_node} at ({G.nodes[dest_node]['y']:.6f}, {G.nodes[dest_node]['x']:.6f})")
    
    # Find routes
    if args.compare or args.algorithm == 'both':
        astar_result, dijkstra_result, metrics = compare_algorithms(G, source_node, dest_node)
        
        if not args.quiet:
            print_route_info(astar_result, "A* Route")
            print_route_info(dijkstra_result, "Dijkstra Route")
            
            print(f"\nComparison:")
            print(f"  Paths identical: {metrics['paths_equal']}")
            print(f"  A* time: {metrics['astar_time_sec']*1000:.2f} ms")
            print(f"  Dijkstra time: {metrics['dijkstra_time_sec']*1000:.2f} ms")
        
        # Create comparison map
        comparison_map_path = os.path.join(args.output_dir, 'route_comparison.html')
        create_comparison_map(
            G, astar_result, dijkstra_result,
            labels=('A* Route', 'Dijkstra Route'),
            output_path=comparison_map_path
        )
        
        # Export outputs for A* route (the main one)
        primary_route = astar_result
        
    elif args.algorithm == 'dijkstra':
        dijkstra_result = dijkstra_path(G, source_node, dest_node)
        
        if dijkstra_result is None:
            print("Error: No path found!")
            return 1
        
        if not args.quiet:
            print_route_info(dijkstra_result, "Dijkstra Route")
        
        primary_route = dijkstra_result
        
    else:  # astar
        astar_result = a_star_path(G, source_node, dest_node)
        
        if astar_result is None:
            print("Error: No path found!")
            return 1
        
        if not args.quiet:
            print_route_info(astar_result, "A* Route")
        
        primary_route = astar_result
    
    # Create route map
    map_path = os.path.join(args.output_dir, 'evacuation_route_map.html')
    create_route_map(
        G, primary_route,
        output_path=map_path,
        show_network=args.show_network,
        start_point=source_point,
        end_point=dest_point
    )
    
    # Create static map
    static_path = os.path.join(args.output_dir, 'evacuation_route_static.png')
    create_static_route_map(G, primary_route, output_path=static_path)
    
    # Export all formats if requested
    if args.export_all:
        outputs = export_all_formats(primary_route, G, output_dir=args.output_dir)
        if not args.quiet:
            print("\nExported files:")
            for fmt, path in outputs.items():
                print(f"  {fmt}: {path}")
    
    if not args.quiet:
        print("\n" + "=" * 60)
        print("OUTPUT FILES")
        print("=" * 60)
        print(f"Interactive map: {map_path}")
        print(f"Static map: {static_path}")
        if args.export_all:
            print(f"CSV route: {args.output_dir}/evacuation_route.csv")
            print(f"GeoJSON route: {args.output_dir}/evacuation_route.geojson")
            print(f"Route summary: {args.output_dir}/evacuation_route_summary.txt")
        if args.compare or args.algorithm == 'both':
            print(f"Comparison map: {comparison_map_path}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())