from sqlalchemy import Column, Integer, String, Float, JSON
from geoalchemy2 import Geometry
from .database import Base
from pydantic import BaseModel
from typing import Optional, Dict

class Ward(Base):
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(String, unique=True, index=True)
    ward_name = Column(String)
    geometry = Column(Geometry('MULTIPOLYGON', srid=4326))
    
    # Scores
    access_score = Column(Float)
    opportunity_score = Column(Float)
    environment_score = Column(Float)
    governance_score = Column(Float)
    uei_score = Column(Float)
    
    # Analytics
    cluster_id = Column(Integer)
    ward_typology = Column(String)
    hotspot_type = Column(String)
    
    # Full data as JSON for flexibility
    properties = Column(JSON)

# Pydantic Models
class WardBase(BaseModel):
    ward_id: str
    ward_name: Optional[str] = None
    uei_score: Optional[float] = None
    ward_typology: Optional[str] = None

class WardOut(WardBase):
    access_score: Optional[float]
    opportunity_score: Optional[float]
    environment_score: Optional[float]
    governance_score: Optional[float]
    hotspot_type: Optional[str]
    
    class Config:
        orm_mode = True

class WardGeoJSON(BaseModel):
    type: str = "Feature"
    geometry: Dict
    properties: Dict
