import json
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Ward, Base
import geopandas as gpd
from shapely import wkt

def load_wards(json_file="processed_data/ward_analytics.geojson"):
    db = SessionLocal()
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Load GeoJSON
    gdf = gpd.read_file(json_file)
    
    for idx, row in gdf.iterrows():
        # Check if exists
        existing = db.query(Ward).filter(Ward.ward_id == str(row['id'])).first()
        if existing:
            continue
            
        ward = Ward(
            ward_id=str(row['id']),
            ward_name=row['name'],
            # geometry=row['geometry'].wkt, # GeoAlchemy2 handles WKT automatically usually, or use ST_GeomFromText
            # For simplicity in this script, we might skip geometry insertion if DB is not PostGIS enabled yet
            # But let's assume it is.
            access_score=row.get('ACCESS_SCORE', 0),
            opportunity_score=row.get('OPPORTUNITY_SCORE', 0),
            environment_score=row.get('ENVIRONMENT_SCORE', 0),
            governance_score=row.get('GOVERNANCE_SCORE', 0),
            uei_score=row.get('UEI_SCORE', 0),
            cluster_id=row.get('Cluster_ID', 0),
            ward_typology=row.get('Ward_Typology', ''),
            hotspot_type=row.get('Hotspot_Type', ''),
            properties=json.loads(row.to_json())
        )
        db.add(ward)
    
    db.commit()
    db.close()
    print("Data loaded into database.")

if __name__ == "__main__":
    load_wards()
