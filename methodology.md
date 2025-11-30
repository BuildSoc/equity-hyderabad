# UEI Methodology Report

## 1. Introduction
The Urban Equitability Index (UEI) measures spatial equity in Hyderabad by analyzing access to services, economic opportunities, environmental quality, and governance.

## 2. Domains & Indicators

### ACCESS
- **Schools**: Density of affordable schools per sq.km.
- **Healthcare**: Density of government hospitals and PHCs.
- **Transit**: Density of bus stops, metro stations, and MMTS stops.

### OPPORTUNITY
- **Commercial Activity**: Density of commercial and industrial points.
- **Financial Services**: Density of Fair Price Shops (proxy for basic services).

### ENVIRONMENT
- **Green Space**: Density of parks.
- **Noise Pollution**: Average noise levels (inverted).

### GOVERNANCE
- **Participation**: Density of Area Sabhas and Ward Committees.

## 3. Data Processing
1. **Standardization**: All layers converted to EPSG:4326.
2. **Geometry Repair**: Invalid geometries fixed, empty geometries removed.
3. **Aggregation**: Point-in-polygon counts computed for each GHMC ward.
4. **Normalization**: Indicators normalized by ward area (density) and then Min-Max scaled (0-1).

## 4. Scoring
- **Entropy Weighting**: Weights for each indicator within a domain are calculated using the Entropy method to avoid subjective bias.
- **Domain Scores**: Weighted sum of normalized indicators.
- **Composite UEI**: Average of domain scores.

## 5. Spatial Analytics
- **Moran's I**: Global measure of spatial autocorrelation to detect clustering of high/low equity.
- **Hotspot Detection**: Z-scores of UEI scores to identify high-equity (Hotspots) and low-equity (Coldspots) wards.
- **Ward Typology**:
    - **PCA**: Dimensionality reduction of domain scores to 2 components.
    - **K-Means Clustering**: Grouping wards into 4 types (A, B, C, D) based on their multidimensional performance.

## 6. Limitations
- **Data Gaps**: Some datasets had missing geometries or attributes.
- **Proxies**: FPS used as proxy for financial access due to lack of bank data.
- **Distance vs Density**: Current version uses density; future versions should incorporate network-based travel time.
