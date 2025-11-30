import h3
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, Point
import logging
import json

logger = logging.getLogger(__name__)

def generate_hex_grid(boundary_gdf, resolution=9):
    """
    Generates an H3 hexagonal grid covering the given boundary.
    
    Args:
        boundary_gdf (GeoDataFrame): A GeoDataFrame containing the boundary polygon(s).
        resolution (int): H3 resolution (default 9).
        
    Returns:
        GeoDataFrame: A GeoDataFrame of hexagons with 'hex_id' and geometry.
    """
    logger.info(f"Generating H3 grid at resolution {resolution}...")
    
    # Ensure CRS is 4326
    if boundary_gdf.crs != "EPSG:4326":
        boundary_gdf = boundary_gdf.to_crs("EPSG:4326")
    
    # Dissolve boundary to get a single geometry
    boundary_geom = boundary_gdf.unary_union
    
    hex_ids = set()
    
    if boundary_geom.geom_type == 'Polygon':
        polys = [boundary_geom]
    elif boundary_geom.geom_type == 'MultiPolygon':
        polys = boundary_geom.geoms
    else:
        raise ValueError("Boundary must be Polygon or MultiPolygon")
        
    for poly in polys:
        # H3 v4 expects GeoJSON-like dictionary for polygon_to_cells
        # But it seems h3.polygon_to_cells takes a polygon object? 
        # No, it takes a geometry object which is a GeoJSON-like dict.
        
        # Construct GeoJSON-like dict manually to be safe
        # H3 expects (lat, lng)? No, v4 is standard GeoJSON (lng, lat) usually?
        # Wait, h3-py v4 documentation says:
        # h3.polygon_to_cells(polygon, res)
        # polygon: GeoJSON-like dictionary.
        
        # Let's use shapely's mapping
        geojson = gpd.GeoSeries([poly]).__geo_interface__['features'][0]['geometry']
        
        try:
            # h3.geo_to_cells(geojson, res)
            # This works with GeoJSON-like dictionaries
            cells = h3.geo_to_cells(geojson, resolution)
            hex_ids.update(cells)
        except Exception as e:
            logger.error(f"Error filling polygon: {e}")
            # Fallback or retry?
            continue

    logger.info(f"Generated {len(hex_ids)} hexagons.")
    return create_hex_gdf(hex_ids)

def create_hex_gdf(hex_ids):
    """
    Converts a set of hex_ids to a GeoDataFrame.
    """
    hex_ids_out = []
    polys = []
    
    for hid in hex_ids:
        try:
            # h3.cell_to_boundary(h) returns ((lat, lng), ...) in v4
            coords_latlng = h3.cell_to_boundary(hid)
            # Swap to (lng, lat) for Shapely/GeoJSON
            coords = [(lng, lat) for lat, lng in coords_latlng]
            
            # coords is a tuple of tuples. Shapely Polygon expects list of tuples.
            polys.append(Polygon(coords))
            hex_ids_out.append(hid)
        except Exception as e:
            logger.error(f"Error converting hex {hid}: {e}")
            
    gdf = gpd.GeoDataFrame({'hex_id': hex_ids_out, 'geometry': polys}, crs="EPSG:4326")
    return gdf
