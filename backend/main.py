from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import wards
from .database import engine, Base

# Create tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not connect to database. Running in offline mode. Error: {e}")

app = FastAPI(
    title="Urban Equitability Index (UEI) API",
    description="API for Hyderabad Urban Equitability Index Platform",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(wards.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to UEI Platform API"}
