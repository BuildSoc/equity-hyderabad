import os
import geopandas as gpd
import pandas as pd
from shapely.validation import make_valid
from shapely.geometry import Point
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SPATIAL_DATA_DIR = Path("Spatial Data")
PROCESSED_DATA_DIR = Path("processed_data")

def fix_geometries(gdf):
    """
    Fix invalid geometries and remove empty ones.
    """
    initial_count = len(gdf)
    
    # Remove None geometries
    gdf = gdf[gdf.geometry.notna()]
    
    # Fix invalid geometries
    if not gdf.geometry.is_valid.all():
        logger.info("Fixing invalid geometries...")
        gdf['geometry'] = gdf.geometry.apply(lambda geom: make_valid(geom) if not geom.is_valid else geom)
    
    # Remove empty geometries
    gdf = gdf[~gdf.geometry.is_empty]
    
    # Explode multiparts if necessary (optional, depending on use case, but usually good for analysis)
    # gdf = gdf.explode(index_parts=True) 
    
    final_count = len(gdf)
    if initial_count != final_count:
        logger.info(f"Removed {initial_count - final_count} empty/null geometries.")
        
    return gdf

def load_and_process_data():
    """
    Load all spatial data, standardize CRS, fix geometries, and generate metadata.
    """
    if not PROCESSED_DATA_DIR.exists():
        PROCESSED_DATA_DIR.mkdir(parents=True)

    metadata = []
    
    # List of files to ignore or handle differently if needed
    ignore_files = ['.DS_Store']

    for file_path in SPATIAL_DATA_DIR.glob("*"):
        if file_path.name in ignore_files:
            continue
            
        try:
            logger.info(f"Processing {file_path.name}...")
            
            if file_path.suffix.lower() == '.geojson':
                gdf = gpd.read_file(file_path)
            elif file_path.suffix.lower() == '.csv':
                # Attempt to load CSV with lat/lon if present
                df = pd.read_csv(file_path)
                # Heuristic to find geometry columns
                if 'lat' in df.columns.str.lower() and 'lon' in df.columns.str.lower():
                     # find exact column names
                    lat_col = df.columns[df.columns.str.lower() == 'lat'][0]
                    lon_col = df.columns[df.columns.str.lower() == 'lon'][0]
                    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]))
                else:
                    logger.warning(f"CSV {file_path.name} does not appear to have lat/lon columns. Skipping geometry conversion.")
                    # Save as regular CSV in processed
                    df.to_csv(PROCESSED_DATA_DIR / file_path.name, index=False)
                    metadata.append({
                        'file_name': file_path.name,
                        'crs': 'N/A',
                        'feature_count': len(df),
                        'geometry_type': 'None',
                        'status': 'Processed (Tabular)'
                    })
                    continue
            else:
                logger.warning(f"Unsupported file type: {file_path.suffix}. Skipping.")
                continue

            # Standardize CRS to EPSG:4326
            if gdf.crs is None:
                logger.warning(f"{file_path.name} has no CRS. Assuming EPSG:4326.")
                gdf.set_crs(epsg=4326, inplace=True)
            elif gdf.crs.to_string() != 'EPSG:4326':
                gdf = gdf.to_crs(epsg=4326)
            
            # Fix geometries
            gdf = fix_geometries(gdf)
            
            # Save processed file
            output_path = PROCESSED_DATA_DIR / file_path.name
            gdf.to_file(output_path, driver='GeoJSON')
            
            metadata.append({
                'file_name': file_path.name,
                'crs': gdf.crs.to_string(),
                'feature_count': len(gdf),
                'geometry_type': gdf.geom_type.mode()[0] if not gdf.empty else 'Empty',
                'status': 'Processed (Spatial)'
            })
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {str(e)}")
            metadata.append({
                'file_name': file_path.name,
                'status': f"Error: {str(e)}"
            })

    # Save metadata catalog
    metadata_df = pd.DataFrame(metadata)
    metadata_df.to_csv(PROCESSED_DATA_DIR / "metadata_catalog.csv", index=False)
    logger.info("Data processing complete. Metadata catalog generated.")

if __name__ == "__main__":
    load_and_process_data()
