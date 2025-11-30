import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from shapely.geometry import Point

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = Path("processed_data")

class IndicatorEngine:
    def __init__(self, data_dir=PROCESSED_DATA_DIR):
        self.data_dir = data_dir
        self.wards = self._load_wards()
        
    def _load_wards(self):
        logger.info("Loading ward boundaries...")
        wards_path = self.data_dir / "ghmc-wards.geojson"
        if not wards_path.exists():
            raise FileNotFoundError("ghmc-wards.geojson not found in processed data.")
        return gpd.read_file(wards_path)

    def _count_points_in_polygon(self, points_gdf, polygon_gdf, count_col_name):
        """
        Count points within each polygon.
        """
        # Ensure CRS match
        if points_gdf.crs != polygon_gdf.crs:
            points_gdf = points_gdf.to_crs(polygon_gdf.crs)
            
        joined = gpd.sjoin(points_gdf, polygon_gdf, how="inner", predicate="within")
        counts = joined.index_right.value_counts().rename(count_col_name)
        return counts

    def calculate_access(self):
        logger.info("Calculating ACCESS indicators...")
        
        # 1. Schools
        try:
            schools = gpd.read_file(self.data_dir / "Affordable Schools (Govt _ Pvt Aided).geojson")
            school_counts = self._count_points_in_polygon(schools, self.wards, "school_count")
            self.wards = self.wards.join(school_counts).fillna({'school_count': 0})
        except Exception as e:
            logger.warning(f"Could not calculate schools: {e}")
            self.wards['school_count'] = 0

        # 2. Hospitals (Combine Govt and Private if available, or just Govt)
        try:
            hospitals = gpd.read_file(self.data_dir / "Govt Hospitals.geojson")
            # Add PHCs
            phcs = gpd.read_file(self.data_dir / "Govt Primary Health Clinics.geojson")
            all_health = pd.concat([hospitals, phcs])
            health_counts = self._count_points_in_polygon(all_health, self.wards, "health_count")
            self.wards = self.wards.join(health_counts).fillna({'health_count': 0})
        except Exception as e:
            logger.warning(f"Could not calculate health: {e}")
            self.wards['health_count'] = 0

        # 3. Transit (Bus Stops + Metro + MMTS)
        try:
            bus = gpd.read_file(self.data_dir / "Bus Stops.geojson")
            metro = gpd.read_file(self.data_dir / "Hyderabad_metro_stations.geojson")
            mmts = gpd.read_file(self.data_dir / "Hyderabad_MMTS_stops.geojson")
            all_transit = pd.concat([bus, metro, mmts])
            transit_counts = self._count_points_in_polygon(all_transit, self.wards, "transit_count")
            self.wards = self.wards.join(transit_counts).fillna({'transit_count': 0})
        except Exception as e:
            logger.warning(f"Could not calculate transit: {e}")
            self.wards['transit_count'] = 0
            
        return self.wards

    def calculate_opportunity(self):
        logger.info("Calculating OPPORTUNITY indicators...")
        
        # 1. Commercial Density (Points)
        try:
            commercial = gpd.read_file(self.data_dir / "Commercial _ Industrial Buildings and Zones (points).geojson")
            comm_counts = self._count_points_in_polygon(commercial, self.wards, "commercial_count")
            self.wards = self.wards.join(comm_counts).fillna({'commercial_count': 0})
        except Exception as e:
            logger.warning(f"Could not calculate commercial: {e}")
            self.wards['commercial_count'] = 0
            
        # 2. Financial Access (FPS as proxy for basic services/banks if banks missing)
        try:
            fps = gpd.read_file(self.data_dir / "FPS.geojson")
            fps_counts = self._count_points_in_polygon(fps, self.wards, "fps_count")
            self.wards = self.wards.join(fps_counts).fillna({'fps_count': 0})
        except Exception as e:
            logger.warning(f"Could not calculate FPS: {e}")
            self.wards['fps_count'] = 0

        return self.wards

    def calculate_environment(self):
        logger.info("Calculating ENVIRONMENT indicators...")
        
        # 1. Parks
        try:
            parks = gpd.read_file(self.data_dir / "GHMC _ HMDA Parks.geojson")
            park_counts = self._count_points_in_polygon(parks, self.wards, "park_count")
            self.wards = self.wards.join(park_counts).fillna({'park_count': 0})
        except Exception as e:
            logger.warning(f"Could not calculate parks: {e}")
            self.wards['park_count'] = 0
            
        # 2. Noise Pollution (Point/Polygon intersection)
        # Assuming Noise Pollution files are points or polygons with values
        try:
            noise = gpd.read_file(self.data_dir / "2018 Jan-June Noise Pollution - Day-Time.geojson")
            # If noise is points, take average within ward
            if noise.geom_type.mode()[0] == 'Point':
                # Ensure CRS
                if noise.crs != self.wards.crs:
                    noise = noise.to_crs(self.wards.crs)
                
                # Spatial join and group by ward to get mean noise
                # Assuming there is a column like 'Leq' or similar. Need to check columns.
                # For now, just count as a proxy for monitoring stations? No, that's bad.
                # Let's try to find a numeric column.
                numeric_cols = noise.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    col = numeric_cols[0] # Take first numeric column
                    joined = gpd.sjoin(noise, self.wards, how="inner", predicate="within")
                    # Group by index of wards (which is preserved in right index if we join wards to noise, but here we joined noise to wards)
                    # sjoin: left_df, right_df. Result has index of left_df.
                    # We want to aggregate noise (left) by ward (right).
                    joined = gpd.sjoin(noise, self.wards, how="inner", predicate="within")
                    ward_noise = joined.groupby('index_right')[col].mean().rename('noise_level')
                    self.wards = self.wards.join(ward_noise).fillna({'noise_level': 0})
                else:
                    self.wards['noise_level'] = 0
            else:
                self.wards['noise_level'] = 0
        except Exception as e:
            logger.warning(f"Could not calculate noise: {e}")
            self.wards['noise_level'] = 0

        return self.wards

    def calculate_governance(self):
        logger.info("Calculating GOVERNANCE indicators...")
        
        # 1. Area Sabhas / Ward Committees (Participation)
        try:
            sabhas = gpd.read_file(self.data_dir / "Area Sabhas.geojson")
            sabha_counts = self._count_points_in_polygon(sabhas, self.wards, "sabha_count")
            self.wards = self.wards.join(sabha_counts).fillna({'sabha_count': 0})
        except Exception as e:
            logger.warning(f"Could not calculate sabhas: {e}")
            self.wards['sabha_count'] = 0
            
        return self.wards

    def run(self):
        self.calculate_access()
        self.calculate_opportunity()
        self.calculate_environment()
        self.calculate_governance()
        
        # Calculate densities (per sq km)
        # Project to UTM for area calculation (Hyderabad is approx UTM 44N)
        # EPSG:32644
        wards_proj = self.wards.to_crs(epsg=32644)
        area_sqkm = wards_proj.geometry.area / 10**6
        self.wards['area_sqkm'] = area_sqkm
        
        # Normalize counts by area
        for col in ['school_count', 'health_count', 'transit_count', 'commercial_count', 'fps_count', 'park_count', 'sabha_count']:
            if col in self.wards.columns:
                self.wards[f'{col}_density'] = self.wards[col] / self.wards['area_sqkm']
        
        output_path = self.data_dir / "wards_with_indicators.geojson"
        self.wards.to_file(output_path, driver='GeoJSON')
        logger.info(f"Indicators calculated and saved to {output_path}")
        return output_path

if __name__ == "__main__":
    engine = IndicatorEngine()
    engine.run()
