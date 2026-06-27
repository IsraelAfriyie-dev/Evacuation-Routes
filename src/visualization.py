"""Visualization module for evacuation route maps.

This module creates interactive (Folium) and static (Matplotlib) maps
showing evacuation routes and road networks.
"""

import os
import networkx as nx
import geopandas as gpd
import folium
from folium import plugins
from shapely.geometry import LineString, Point
from typing import List, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from routing import RouteResult


def create_route_map(
    G: nx.MultiDiGraph,
    route: RouteResult,
    output_path: str = 'outputs/evacuation_route_map.html',
    show_network: bool = False,
    start_point: Optional[Tuple[float, float]] = None,
    end_point: Optional[Tuple[float, float]] = None
) -> folium.Map:
    """Create an interactive Folium map showing the evacuation route.
    
    Args:
        G: NetworkX graph
        route: RouteResult containing the path
        output_path: Path to save the HTML map
        show_network: Whether to show the full road network
        start_point: Optional (lat, lon) tuple for start marker
        end_point: Optional (lat, lon) tuple for end marker
    
    Returns:
        Folium Map object
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    # Calculate map center
    if route.path:
        node = route.path[len(route.path) // 2]
        center_lat = G.nodes[node]['y']
        center_lon = G.nodes[node]['x']
    else:
        center_lat, center_lon = 44.2601, -72.5754
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Add terrain layer option
    folium.TileLayer('cartodbpositron', name='Light Map').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Topographic Map'
    ).add_to(m)
    
    # Add full network if requested
    if show_network:
        print("Adding road network to map (this may take a moment)...")
        import osmnx as ox
        gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        
        for idx, row in gdf_edges.iterrows():
            if hasattr(row.geometry, 'coords') and row.geometry is not None:
                coords = [[coord[1], coord[0]] for coord in row.geometry.coords]
                folium.PolyLine(
                    coords,
                    color='#888888',
                    weight=1,
                    opacity=0.5
                ).add_to(m)
    
    # Create route geometry
    if route.path and len(route.path) > 1:
        route_coords = []
        for node in route.path:
            route_coords.append([G.nodes[node]['y'], G.nodes[node]['x']])
        
        # Add route polyline
        folium.PolyLine(
            route_coords,
            color='#ff3300',
            weight=5,
            opacity=0.8,
            popup=f"Evacuation Route<br>Distance: {route.distance_km:.2f} km<br>Time: {route.travel_time_minutes:.1f} min"
        ).add_to(m)
        
        # Add start marker
        start_node = route.path[0]
        start_lat = G.nodes[start_node]['y']
        start_lon = G.nodes[start_node]['x']
        
        if start_point:
            start_lat, start_lon = start_point
        
        folium.Marker(
            [start_lat, start_lon],
            popup=f'Start<br>Node: {start_node}',
            icon=folium.Icon(color='green', icon='play', prefix='fa'),
            tooltip='Evacuation Start'
        ).add_to(m)
        
        # Add end marker
        end_node = route.path[-1]
        end_lat = G.nodes[end_node]['y']
        end_lon = G.nodes[end_node]['x']
        
        if end_point:
            end_lat, end_lon = end_point
        
        folium.Marker(
            [end_lat, end_lon],
            popup=f'Destination<br>Node: {end_node}',
            icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa'),
            tooltip='Evacuation Destination'
        ).add_to(m)
        
        # Add waypoint markers for long routes
        if len(route.path) > 10:
            step = max(1, len(route.path) // 10)
            for i in range(0, len(route.path), step):
                if i > 0 and i < len(route.path) - 1:
                    node = route.path[i]
                    folium.CircleMarker(
                        [G.nodes[node]['y'], G.nodes[node]['x']],
                        radius=4,
                        color='#ff6600',
                        fill=True,
                        fillColor='#ff9933',
                        fillOpacity=0.8,
                        popup=f'Waypoint {i}<br>Node: {node}'
                    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add fullscreen option
    plugins.Fullscreen().add_to(m)
    
    # Add measure control
    plugins.MeasureControl(position='bottomleft').add_to(m)
    
    # Add title
    title_html = '''
    <div style="position: fixed; 
                top: 10px; left: 50px; width: 400px; 
                z-index:9999; font-size:14px;
                background-color: white; padding: 10px;
                border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
        <b>🚨 Evacuation Route Map</b><br>
        <span style="color: #ff3300;">━━━</span> Evacuation Route<br>
        <span style="color: #888888;">━━━</span> Road Network (optional)<br>
        <span style="color: green;">▶</span> Start Point<br>
        <span style="color: red;">⚑</span> Destination
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Save map
    m.save(output_path)
    print(f"Map saved to {output_path}")
    
    return m


def create_comparison_map(
    G: nx.MultiDiGraph,
    route1: RouteResult,
    route2: RouteResult,
    labels: Tuple[str, str] = ('A* Route', 'Dijkstra Route'),
    output_path: str = 'outputs/route_comparison_map.html'
) -> folium.Map:
    """Create a map comparing two routes.
    
    Args:
        G: NetworkX graph
        route1: First RouteResult
        route2: Second RouteResult
        labels: Tuple of labels for the two routes
        output_path: Path to save the HTML map
    
    Returns:
        Folium Map object
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    # Calculate map center
    if route1.path:
        node = route1.path[len(route1.path) // 2]
        center_lat = G.nodes[node]['y']
        center_lon = G.nodes[node]['x']
    else:
        center_lat, center_lon = 44.2601, -72.5754
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Add route 1 (A*) in blue
    if route1.path and len(route1.path) > 1:
        route1_coords = [[G.nodes[n]['y'], G.nodes[n]['x']] for n in route1.path]
        folium.PolyLine(
            route1_coords,
            color='#0066ff',
            weight=5,
            opacity=0.8,
            popup=f"{labels[0]}<br>Distance: {route1.distance_km:.2f} km<br>Time: {route1.travel_time_minutes:.1f} min"
        ).add_to(m)
        
        # Start and end markers for route 1
        folium.Marker(
            [G.nodes[route1.path[0]]['y'], G.nodes[route1.path[0]]['x']],
            icon=folium.Icon(color='blue', icon='play', prefix='fa'),
            tooltip=labels[0]
        ).add_to(m)
        
    # Add route 2 (Dijkstra) in orange
    if route2.path and len(route2.path) > 1:
        route2_coords = [[G.nodes[n]['y'], G.nodes[n]['x']] for n in route2.path]
        folium.PolyLine(
            route2_coords,
            color='#ff9900',
            weight=5,
            opacity=0.8,
            popup=f"{labels[1]}<br>Distance: {route2.distance_km:.2f} km<br>Time: {route2.travel_time_minutes:.1f} min"
        ).add_to(m)
        
        # Start and end markers for route 2
        folium.Marker(
            [G.nodes[route2.path[0]]['y'], G.nodes[route2.path[0]]['x']],
            icon=folium.Icon(color='orange', icon='play', prefix='fa'),
            tooltip=labels[1]
        ).add_to(m)
    
    # Add shared destination marker
    if route1.path and route2.path:
        dest_node = route1.path[-1]
        folium.Marker(
            [G.nodes[dest_node]['y'], G.nodes[dest_node]['x']],
            icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa'),
            tooltip='Destination'
        ).add_to(m)
    
    # Add title
    title_html = f'''
    <div style="position: fixed; 
                top: 10px; left: 50px; width: 350px; 
                z-index:9999; font-size:14px;
                background-color: white; padding: 10px;
                border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
        <b>🔍 Route Comparison</b><br>
        <span style="color: #0066ff;">━━━</span> {labels[0]}<br>
        <span style="color: #ff9900;">━━━</span> {labels[1]}
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Save map
    m.save(output_path)
    print(f"Comparison map saved to {output_path}")
    
    return m


def create_static_route_map(
    G: nx.MultiDiGraph,
    route: RouteResult,
    output_path: str = 'outputs/evacuation_route_static.png',
    figsize: Tuple[int, int] = (12, 10)
) -> plt.Figure:
    """Create a static Matplotlib map of the evacuation route.
    
    Args:
        G: NetworkX graph
        route: RouteResult containing the path
        output_path: Path to save the image
        figsize: Figure size tuple
    
    Returns:
        Matplotlib Figure object
    """
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    
    # Get route coordinates
    if route.path:
        route_lats = [G.nodes[n]['y'] for n in route.path]
        route_lons = [G.nodes[n]['x'] for n in route.path]
        
        # Plot route
        ax.plot(route_lons, route_lats, 'r-', linewidth=3, label='Evacuation Route', zorder=3)
        ax.plot(route_lons, route_lats, 'ro', markersize=6, zorder=4)
        
        # Mark start and end
        ax.plot(route_lons[0], route_lats[0], 'go', markersize=12, label='Start', zorder=5)
        ax.plot(route_lons[-1], route_lats[-1], 'rs', markersize=12, label='Destination', zorder=5)
        
        # Get network bounds for context
        all_lats = route_lats
        all_lons = route_lons
    else:
        all_lats = [G.nodes[n]['y'] for n in G.nodes()]
        all_lons = [G.nodes[n]['x'] for n in G.nodes()]
    
    # Plot some network edges for context (sample if many)
    edge_count = 0
    max_edges_to_show = 500
    for u, v in G.edges():
        if edge_count >= max_edges_to_show:
            break
        u_lat = G.nodes[u]['y']
        u_lon = G.nodes[u]['x']
        v_lat = G.nodes[v]['y']
        v_lon = G.nodes[v]['x']
        ax.plot([u_lon, v_lon], [u_lat, v_lat], 'k-', linewidth=0.3, alpha=0.3, zorder=1)
        edge_count += 1
    
    # Set axis limits with padding
    if route.path:
        lat_margin = (max(route_lats) - min(route_lats)) * 0.1 or 0.01
        lon_margin = (max(route_lons) - min(route_lons)) * 0.1 or 0.01
        ax.set_xlim(min(route_lons) - lon_margin, max(route_lons) + lon_margin)
        ax.set_ylim(min(route_lats) - lat_margin, max(route_lats) + lat_margin)
    
    # Labels and title
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title(f'Evacuation Route\nDistance: {route.distance_km:.2f} km | Travel Time: {route.travel_time_minutes:.1f} min')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Add info box
    info_text = f'Nodes: {len(route.path)}\nEdges: {len(route.edges)}'
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Static map saved to {output_path}")
    
    return fig


def create_multi_route_map(
    G: nx.MultiDiGraph,
    routes: List[RouteResult],
    output_path: str = 'outputs/multi_route_map.html',
    colors: Optional[List[str]] = None
) -> folium.Map:
    """Create a map showing multiple evacuation routes.
    
    Args:
        G: NetworkX graph
        routes: List of RouteResult objects
        output_path: Path to save the HTML map
        colors: Optional list of colors for each route
    
    Returns:
        Folium Map object
    """
    if colors is None:
        colors = ['#ff3300', '#0066ff', '#33cc33', '#cc00cc', '#ff9900']
    
    # Calculate map center
    if routes and routes[0].path:
        node = routes[0].path[len(routes[0].path) // 2]
        center_lat = G.nodes[node]['y']
        center_lon = G.nodes[node]['x']
    else:
        center_lat, center_lon = 44.2601, -72.5754
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Add each route
    for i, route in enumerate(routes):
        if route.path and len(route.path) > 1:
            route_coords = [[G.nodes[n]['y'], G.nodes[n]['x']] for n in route.path]
            color = colors[i % len(colors)]
            
            folium.PolyLine(
                route_coords,
                color=color,
                weight=5,
                opacity=0.8,
                popup=f'Route {i+1}<br>Distance: {route.distance_km:.2f} km<br>Time: {route.travel_time_minutes:.1f} min'
            ).add_to(m)
            
            # Add markers
            folium.Marker(
                [G.nodes[route.path[0]]['y'], G.nodes[route.path[0]]['x']],
                icon=folium.Icon(color='green', icon='play', prefix='fa'),
                tooltip=f'Route {i+1} Start'
            ).add_to(m)
            
            folium.Marker(
                [G.nodes[route.path[-1]]['y'], G.nodes[route.path[-1]]['x']],
                icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa'),
                tooltip=f'Route {i+1} Destination'
            ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save map
    m.save(output_path)
    print(f"Multi-route map saved to {output_path}")
    
    return m


if __name__ == '__main__':
    # Test visualization module
    import sys
    sys.path.insert(0, '.')
    
    from data_loader import load_or_download_network, get_node_nearest_to_point
    from routing import a_star_path
    
    print("Testing visualization module...")
    
    # Load network
    G = load_or_download_network(dist_km=5)
    
    # Find a test route
    source_point = (44.2601, -72.5754)
    target_point = (44.2200, -72.5800)
    
    source_node = get_node_nearest_to_point(G, source_point)
    target_node = get_node_nearest_to_point(G, target_point)
    
    route = a_star_path(G, source_node, target_node)
    
    if route:
        print(f"\nCreating maps for route with {len(route.path)} nodes...")
        
        # Create interactive map
        create_route_map(G, route, show_network=True)
        
        # Create static map
        create_static_route_map(G, route)