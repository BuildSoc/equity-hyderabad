# Urban Equitability Index (UEI) Platform - Hyderabad

## Overview
The UEI Platform is a comprehensive tool to measure and visualize spatial equity across Hyderabad's wards. It integrates data from various domains—Access, Opportunity, Environment, and Governance—to compute a composite Urban Equitability Index (UEI) Score.

## Features
- **Data Engine**: Automated pipeline to process spatial data, compute indicators, and generate scores.
- **Interactive Dashboard**: Next.js + Mapbox GL JS frontend to visualize scores and ward typologies.
- **Backend API**: FastAPI + PostGIS backend to serve data and analytics.
- **Spatial Analytics**: Moran's I for spatial autocorrelation, Hotspot detection, and Ward Typology clustering (PCA + KMeans).

## System Architecture
```mermaid
graph TD
    Data[Spatial Data (GeoJSON/CSV)] --> Engine[Data Engine (Python)]
    Engine --> |Process & Score| DB[(PostgreSQL + PostGIS)]
    Engine --> |Export| Files[GeoJSON/CSV Outputs]
    
    API[FastAPI Backend] --> |Query| DB
    API --> |Serve| Frontend[Next.js Dashboard]
    
    Frontend --> |Visualize| Map[Mapbox GL JS]
    Frontend --> |Charts| Charts[Recharts]
```

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.9+ (for local data engine dev)

### Quick Start (Docker)
1. Clone the repository.
2. Run `docker-compose up --build`.
3. Access the dashboard at `http://localhost:3000`.
4. Access the API docs at `http://localhost:8000/docs`.

### Local Development
#### Data Engine
```bash
pip install -r requirements.txt
python -m data_engine.main
```

#### Backend
```bash
uvicorn backend.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Methodology
See [methodology.md](methodology.md) for detailed explanation of indicators and scoring logic.

## Deployment
- **Backend**: Deploy to Railway or Render using the provided `Dockerfile.backend`.
- **Frontend**: Deploy to Vercel.
- **Database**: Use a managed PostGIS instance (e.g., Railway, Supabase, AWS RDS).

## License
MIT
