import osmnx as ox
import geopandas as gpd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = Path("processed_data")

def extract_osm_destinations(boundary_gdf):
    """
    Extract additional destination types from OSM.
    """
    # Ensure CRS
    boundary = boundary_gdf.to_crs("EPSG:4326").unary_union
    
    destinations = {}
    
    # Pharmacies
    logger.info("Extracting pharmacies...")
    try:
        pharmacies = ox.features_from_polygon(boundary, tags={'amenity': 'pharmacy'})
        if not pharmacies.empty:
            # Convert to points (centroids)
            pharmacies = pharmacies.to_crs("EPSG:4326")
            pharmacies['geometry'] = pharmacies.geometry.centroid
            destinations['pharmacies'] = pharmacies[['geometry']]
            logger.info(f"Found {len(pharmacies)} pharmacies")
    except Exception as e:
        logger.warning(f"Could not extract pharmacies: {e}")
        
    # Supermarkets
    logger.info("Extracting supermarkets...")
    try:
        supermarkets = ox.features_from_polygon(boundary, tags={'shop': 'supermarket'})
        if not supermarkets.empty:
            supermarkets = supermarkets.to_crs("EPSG:4326")
            supermarkets['geometry'] = supermarkets.geometry.centroid
            destinations['supermarkets'] = supermarkets[['geometry']]
            logger.info(f"Found {len(supermarkets)} supermarkets")
    except Exception as e:
        logger.warning(f"Could not extract supermarkets: {e}")
        
    # Playgrounds
    logger.info("Extracting playgrounds...")
    try:
        playgrounds = ox.features_from_polygon(boundary, tags={'leisure': 'playground'})
        if not playgrounds.empty:
            playgrounds = playgrounds.to_crs("EPSG:4326")
            playgrounds['geometry'] = playgrounds.geometry.centroid
            destinations['playgrounds'] = playgrounds[['geometry']]
            logger.info(f"Found {len(playgrounds)} playgrounds")
    except Exception as e:
        logger.warning(f"Could not extract playgrounds: {e}")
        
    # Libraries
    logger.info("Extracting libraries...")
    try:
        libraries = ox.features_from_polygon(boundary, tags={'amenity': 'library'})
        if not libraries.empty:
            libraries = libraries.to_crs("EPSG:4326")
            libraries['geometry'] = libraries.geometry.centroid
            destinations['libraries'] = libraries[['geometry']]
            logger.info(f"Found {len(libraries)} libraries")
    except Exception as e:
        logger.warning(f"Could not extract libraries: {e}")
        
    # Cultural venues (museums, theaters, arts centers)
    logger.info("Extracting cultural venues...")
    try:
        museums = ox.features_from_polygon(boundary, tags={'tourism': 'museum'})
        theaters = ox.features_from_polygon(boundary, tags={'amenity': 'theatre'})
        arts = ox.features_from_polygon(boundary, tags={'amenity': 'arts_centre'})
        
        cultural = gpd.GeoDataFrame()
        for gdf in [museums, theaters, arts]:
            if not gdf.empty:
                cultural = gpd.GeoDataFrame(pd.concat([cultural, gdf], ignore_index=True))
                
        if not cultural.empty:
            cultural = cultural.to_crs("EPSG:4326")
            cultural['geometry'] = cultural.geometry.centroid
            destinations['cultural'] = cultural[['geometry']]
            logger.info(f"Found {len(cultural)} cultural venues")
    except Exception as e:
        logger.warning(f"Could not extract cultural venues: {e}")
        
    return destinations

if __name__ == "__main__":
    import pandas as pd
    
    # Load wards
    wards = gpd.read_file(PROCESSED_DATA_DIR / "ghmc-wards.geojson")
    
    # Extract destinations
    destinations = extract_osm_destinations(wards)
    
    # Save to files
    for name, gdf in destinations.items():
        output_path = PROCESSED_DATA_DIR / f"{name}.geojson"
        gdf.to_file(output_path, driver='GeoJSON')
        logger.info(f"Saved {name} to {output_path}")
