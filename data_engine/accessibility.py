import osmnx as ox
import networkx as nx
import geopandas as gpd
import pandas as pd
import logging
from shapely.geometry import Point

logger = logging.getLogger(__name__)

# Walking speed in m/s (from paper: 1.26 m/s)
WALK_SPEED = 1.26 

class AccessibilityEngine:
    def __init__(self, network_dist=1500):
        self.G = None
        self.network_dist = network_dist # Buffer for graph download
        
    def load_network(self, polygon):
        """
        Loads the walking network for the given polygon.
        """
        logger.info("Downloading walking network from OSM...")
        # Simplify: True, Network Type: walk
        try:
            self.G = ox.graph_from_polygon(polygon, network_type='walk', simplify=True)
            # Project to UTM for metric distance calculations
            self.G = ox.project_graph(self.G)
            logger.info(f"Network loaded: {len(self.G.nodes)} nodes, {len(self.G.edges)} edges.")
        except Exception as e:
            logger.error(f"Error loading network: {e}")
            raise

    def calculate_accessibility(self, origins_gdf, destinations_dict, thresholds=[5, 15]):
        """
        Calculates accessibility for each origin to each destination type.
        
        Args:
            origins_gdf (GeoDataFrame): Hexagon centroids (Points).
            destinations_dict (dict): Dict of {type: GeoDataFrame} for destinations.
            thresholds (list): List of time thresholds in minutes.
            
        Returns:
            GeoDataFrame: origins_gdf with added count columns.
        """
        if self.G is None:
            raise ValueError("Network not loaded. Call load_network() first.")
            
        # Ensure origins are in same CRS as graph (UTM)
        # ox.project_graph projects to UTM. We need to project points to same.
        # graph_crs = self.G.graph['crs'] # osmnx stores crs in graph attribute? No, usually we check.
        # Actually ox.project_graph returns a graph with UTM CRS.
        # We can get it from the edges or nodes.
        gdf_nodes = ox.graph_to_gdfs(self.G, nodes=True, edges=False)
        graph_crs = gdf_nodes.crs
        
        origins_utm = origins_gdf.to_crs(graph_crs)
        
        # Snap origins to nearest nodes
        logger.info("Snapping origins to network...")
        # Use centroids of hexagons
        origin_centroids = origins_utm.centroid
        origin_nodes = ox.distance.nearest_nodes(self.G, origin_centroids.x, origin_centroids.y)
        origins_gdf['node_id'] = origin_nodes
        
        # Pre-process destinations
        dest_nodes_map = {}
        for dtype, dest_gdf in destinations_dict.items():
            if dest_gdf.empty:
                logger.warning(f"No destinations for {dtype}")
                continue
                
            dest_utm = dest_gdf.to_crs(graph_crs)
            # Use centroids for destinations (some might be polygons)
            dest_centroids = dest_utm.centroid
            d_nodes = ox.distance.nearest_nodes(self.G, dest_centroids.x, dest_centroids.y)
            # Create a series or dict to count destinations at each node
            # Some nodes might have multiple destinations
            dest_counts = pd.Series(d_nodes).value_counts()
            dest_nodes_map[dtype] = dest_counts
            
        # Calculate accessibility
        logger.info("Calculating accessibility counts...")
        
        # Initialize result columns
        for dtype in destinations_dict.keys():
            for t in thresholds:
                origins_gdf[f'{dtype}_{t}min'] = 0
                
        # Iterate over origins
        # Optimization: Use single_source_dijkstra_path_length with cutoff
        # Cutoff distance = time * speed
        
        for i, (idx, row) in enumerate(origins_gdf.iterrows()):
            center_node = row['node_id']
            
            if i % 100 == 0:
                logger.info(f"Processed {i}/{len(origins_gdf)} origins")
            
            # Max distance needed is max threshold
            max_time = max(thresholds)
            max_dist = max_time * 60 * WALK_SPEED
            
            # Get all nodes within max_dist
            # returns {node: dist}
            subgraph_dists = nx.single_source_dijkstra_path_length(self.G, center_node, cutoff=max_dist, weight='length')
            
            # For each threshold, filter nodes and count destinations
            for t in thresholds:
                dist_cutoff = t * 60 * WALK_SPEED
                reachable_nodes = [n for n, d in subgraph_dists.items() if d <= dist_cutoff]
                
                for dtype, d_counts in dest_nodes_map.items():
                    # Sum counts for reachable nodes
                    # Intersection of reachable_nodes and d_counts.index
                    # This is faster:
                    count = 0
                    for node in reachable_nodes:
                        if node in d_counts:
                            count += d_counts[node]
                    
                    origins_gdf.at[idx, f'{dtype}_{t}min'] = count
                    
        return origins_gdf
