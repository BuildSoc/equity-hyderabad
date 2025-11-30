import logging
from pathlib import Path
import geopandas as gpd
import pandas as pd
from .loader import load_and_process_data
from .indicators import IndicatorEngine
from .scoring import ScoringEngine
from .analytics import AnalyticsEngine
from .hex_grid import generate_hex_grid
from .accessibility import AccessibilityEngine
from .equity import EquityEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = Path("processed_data")

def run_x_minute_analysis():
    logger.info("Starting X-Minute City Analysis...")
    
    # 1. Generate Hex Grid
    logger.info("Generating Hex Grid...")
    wards_path = PROCESSED_DATA_DIR / "ghmc-wards.geojson"
    if not wards_path.exists():
        logger.error("Wards file not found. Run Step 1 first.")
        return
        
    wards = gpd.read_file(wards_path)
    # Use Res 9 (approx 0.1 sq km)
    hex_grid = generate_hex_grid(wards, resolution=9)
    
    # 2. Load Network
    logger.info("Loading Walking Network...")
    acc_engine = AccessibilityEngine()
    # Use the union of wards as the boundary for network
    boundary = wards.to_crs("EPSG:4326").unary_union
    acc_engine.load_network(boundary)
    
    # 3. Prepare Destinations
    logger.info("Preparing Destinations...")
    destinations = {}
    
    # Helper to load
    def load_dest(name):
        p = PROCESSED_DATA_DIR / name
        if p.exists():
            return gpd.read_file(p)
        return gpd.GeoDataFrame()
        
    destinations['school'] = load_dest("Affordable Schools (Govt _ Pvt Aided).geojson")
    
    # Health: Hospitals + PHCs
    hosp = load_dest("Govt Hospitals.geojson")
    phc = load_dest("Govt Primary Health Clinics.geojson")
    destinations['health'] = pd.concat([hosp, phc]) if not hosp.empty or not phc.empty else gpd.GeoDataFrame()
    
    # Transit: Bus + Metro + MMTS
    bus = load_dest("Bus Stops.geojson")
    metro = load_dest("Hyderabad_metro_stations.geojson")
    mmts = load_dest("Hyderabad_MMTS_stops.geojson")
    destinations['transit'] = pd.concat([bus, metro, mmts]) if not bus.empty or not metro.empty or not mmts.empty else gpd.GeoDataFrame()
    
    destinations['park'] = load_dest("GHMC _ HMDA Parks.geojson")
    destinations['commercial'] = load_dest("Commercial _ Industrial Buildings and Zones (points).geojson")
    destinations['fps'] = load_dest("FPS.geojson") # Proxy for financial/basic
    
    # New destination types
    destinations['pharmacy'] = load_dest("pharmacies.geojson")
    destinations['supermarket'] = load_dest("supermarkets.geojson")
    destinations['playground'] = load_dest("playgrounds.geojson")
    destinations['library'] = load_dest("libraries.geojson")
    destinations['cultural'] = load_dest("cultural.geojson")
    
    # 4. Calculate Accessibility
    logger.info("Calculating Accessibility...")
    # Calculate for 5 and 15 minutes
    hex_scores = acc_engine.calculate_accessibility(hex_grid, destinations, thresholds=[5, 15])
    
    # 5. Calculate Equity
    logger.info("Calculating Equity Metrics...")
    eq_engine = EquityEngine()
    
    # Egalitarian (Gini)
    # We calculate Gini for the distribution of counts across the city
    # Store Gini in a separate metadata file or log it?
    # The user wants to "Improve this application", likely meaning visualizing the map.
    # But Gini is a global stat. I'll save it to a CSV.
    
    access_cols = [c for c in hex_scores.columns if 'min' in c]
    gini_scores = eq_engine.calculate_egalitarian(hex_scores, access_cols)
    pd.DataFrame.from_dict(gini_scores, orient='index', columns=['gini']).to_csv(PROCESSED_DATA_DIR / "gini_scores.csv")
    
    # Sufficientarian Scores - General
    # All essential types
    all_types_15 = ['school_15min', 'health_15min', 'transit_15min', 'park_15min', 
                    'pharmacy_15min', 'supermarket_15min', 'playground_15min', 'library_15min', 'cultural_15min']
    hex_scores['sufficiency_score_15min'] = eq_engine.calculate_sufficientarian(hex_scores, all_types_15)
    
    all_types_5 = ['school_5min', 'health_5min', 'transit_5min', 'park_5min',
                   'pharmacy_5min', 'supermarket_5min', 'playground_5min', 'library_5min', 'cultural_5min']
    hex_scores['sufficiency_score_5min'] = eq_engine.calculate_sufficientarian(hex_scores, all_types_5)
    
    # Thematic Sufficiency Scores
    themes = {
        'mobility': ['transit_15min'],
        'daily_needs': ['pharmacy_15min', 'supermarket_15min', 'health_15min'],
        'family': ['school_15min', 'park_15min', 'playground_15min'],
        'leisure': ['cultural_15min', 'library_15min', 'park_15min']
    }
    hex_scores = eq_engine.calculate_thematic_sufficiency(hex_scores, themes)
    
    # 5-min thematic scores
    themes_5 = {
        'mobility_5min': ['transit_5min'],
        'daily_needs_5min': ['pharmacy_5min', 'supermarket_5min', 'health_5min'],
        'family_5min': ['school_5min', 'park_5min', 'playground_5min'],
        'leisure_5min': ['cultural_5min', 'library_5min', 'park_5min']
    }
    hex_scores = eq_engine.calculate_thematic_sufficiency(hex_scores, themes_5)

    # Save
    output_path = PROCESSED_DATA_DIR / "hex_accessibility_scores.geojson"
    hex_scores.to_file(output_path, driver='GeoJSON')
    logger.info(f"X-Minute Analysis saved to {output_path}")

def main():
    logger.info("Starting UEI Data Engine Pipeline...")
    
    # 1. Load and Process Data
    logger.info("Step 1: Data Loading & Processing")
    load_and_process_data()
    
    # 2. Calculate Indicators
    logger.info("Step 2: Indicator Computation")
    indicator_engine = IndicatorEngine()
    indicator_engine.run()
    
    # 3. Compute Scores
    logger.info("Step 3: Scoring & Weighting")
    scoring_engine = ScoringEngine()
    scoring_engine.compute_scores()
    
    # 4. Spatial Analytics
    logger.info("Step 4: Spatial Analytics")
    analytics_engine = AnalyticsEngine()
    analytics_engine.run()
    
    # 5. X-Minute City Analysis
    logger.info("Step 5: X-Minute City Analysis")
    run_x_minute_analysis()
    
    logger.info("UEI Pipeline Completed Successfully!")

if __name__ == "__main__":
    main()
