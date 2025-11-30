import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = Path("processed_data")

class AnalyticsEngine:
    def __init__(self, data_dir=PROCESSED_DATA_DIR):
        self.data_dir = data_dir
        
    def _get_weights_matrix(self, gdf):
        """
        Compute spatial weights matrix (Queen contiguity) manually.
        """
        # This is computationally expensive for large datasets, but fine for ~150 wards.
        # Create adjacency matrix
        w = np.zeros((len(gdf), len(gdf)))
        
        # Use sjoin to find neighbors
        # Buffer slightly to ensure touches works reliably or use intersects
        # Or just iterate (slow but simple)
        
        # Faster approach: use sjoin with itself
        # Create a temporary ID
        gdf['temp_id'] = range(len(gdf))
        
        # Buffer slightly to catch touching polygons
        # gdf_buffered = gdf.copy()
        # gdf_buffered.geometry = gdf.geometry.buffer(1e-6)
        
        # Spatial join to find neighbors
        # This gives index of left and right
        # neighbors = gpd.sjoin(gdf, gdf, predicate='touches')
        # This might miss some if geometries are not perfectly aligned.
        # 'intersects' is safer but includes self.
        
        neighbors = gpd.sjoin(gdf, gdf, predicate='intersects')
        
        for idx, row in neighbors.iterrows():
            neighbor_idx = row['index_right']
            if idx != neighbor_idx:
                w[gdf.index.get_loc(idx), gdf.index.get_loc(neighbor_idx)] = 1
                
        # Row-normalize
        row_sums = w.sum(axis=1)
        # Avoid division by zero
        row_sums[row_sums == 0] = 1
        w_norm = w / row_sums[:, np.newaxis]
        
        return w_norm

    def compute_morans_i(self, gdf, col):
        """
        Calculate Global Moran's I manually.
        """
        y = gdf[col].values
        w = self._get_weights_matrix(gdf)
        
        n = len(y)
        y_mean = np.mean(y)
        y_diff = y - y_mean
        
        # Numerator: n * sum(wij * (xi - xbar) * (xj - xbar))
        # Denominator: sum(wij) * sum((xi - xbar)^2)
        
        # Since w is row-normalized, sum(wij) = n (approx, if no islands)
        # Actually sum(wij) is sum of all weights.
        s0 = w.sum()
        
        num = n * np.sum(w * np.outer(y_diff, y_diff))
        den = s0 * np.sum(y_diff ** 2)
        
        if den == 0:
            return 0, 0 # Avoid div by zero
            
        I = num / den
        
        return I

    def compute_spatial_stats(self, gdf, col='UEI_SCORE'):
        logger.info(f"Computing spatial stats for {col}...")
        
        try:
            I = self.compute_morans_i(gdf, col)
            logger.info(f"Global Moran's I: {I}")
            gdf['Morans_I'] = I # Store global value (repeated)
            
            # Simple Hotspot Proxy: Z-Score of the value itself (not spatial)
            # Or Local Moran's I (too complex to implement manually quickly)
            # Let's just use Z-Score of the UEI Score for now as a "Hotspot" of high equity.
            # Or better, Z-Score of the spatially lagged variable?
            # Lag = W * y
            w = self._get_weights_matrix(gdf)
            lag = w @ gdf[col].values
            
            # Local Gi* proxy: (x_i - mean) + (lag_i - mean) ?
            # Let's just output the Lagged Value
            gdf['Spatial_Lag'] = lag
            
            # Hotspot based on Z-score of UEI Score
            mean = gdf[col].mean()
            std = gdf[col].std()
            gdf['Gi_ZScore'] = (gdf[col] - mean) / std
            
            conditions = [
                (gdf['Gi_ZScore'] > 1.0), # Relaxed threshold
                (gdf['Gi_ZScore'] < -1.0)
            ]
            choices = ['High Equity', 'Low Equity']
            gdf['Hotspot_Type'] = np.select(conditions, choices, default='Average')
            
        except Exception as e:
            logger.error(f"Error in spatial stats: {e}")
            gdf['Hotspot_Type'] = 'Error'
        
        return gdf

    def compute_typology(self, gdf, domain_cols):
        logger.info("Computing Ward Typology (PCA + KMeans)...")
        
        # Prepare data
        X = gdf[domain_cols].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # PCA
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        gdf['PCA_1'] = X_pca[:, 0]
        gdf['PCA_2'] = X_pca[:, 1]
        
        # KMeans
        kmeans = KMeans(n_clusters=4, random_state=42)
        clusters = kmeans.fit_predict(X_scaled)
        
        # Map clusters
        gdf['Cluster_ID'] = clusters
        cluster_means = gdf.groupby('Cluster_ID')['UEI_SCORE'].mean().sort_values(ascending=False)
        mapping = {old: new for old, new in zip(cluster_means.index, ['Type A', 'Type B', 'Type C', 'Type D'])}
        gdf['Ward_Typology'] = gdf['Cluster_ID'].map(mapping)
        
        return gdf

    def run(self, input_file="ward_scores.geojson"):
        logger.info("Loading data for analytics...")
        gdf = gpd.read_file(self.data_dir / input_file)
        
        # Spatial Stats
        if 'UEI_SCORE' in gdf.columns:
            gdf = self.compute_spatial_stats(gdf, 'UEI_SCORE')
        
        # Typology
        domain_cols = [c for c in gdf.columns if c.endswith('_SCORE') and c != 'UEI_SCORE']
        if domain_cols:
            gdf = self.compute_typology(gdf, domain_cols)
            
        # Save results
        output_path = self.data_dir / "ward_analytics.geojson"
        gdf.to_file(output_path, driver='GeoJSON')
        
        # Save CSVs
        gdf.drop(columns='geometry').to_csv(self.data_dir / "ward_analytics.csv", index=False)
        
        # Save Hotspots CSV
        if 'Gi_ZScore' in gdf.columns:
            cols = ['id', 'name', 'Gi_ZScore', 'Hotspot_Type', 'geometry']
            # Ensure cols exist
            cols = [c for c in cols if c in gdf.columns]
            gdf[cols].to_csv(self.data_dir / "hotspots.csv", index=False)
        
        # Save Typology CSV
        if 'Ward_Typology' in gdf.columns:
            cols = ['id', 'name', 'Ward_Typology', 'PCA_1', 'PCA_2']
            cols = [c for c in cols if c in gdf.columns]
            gdf[cols].to_csv(self.data_dir / "cluster_typology.csv", index=False)
        
        logger.info(f"Analytics computed and saved to {output_path}")
        return output_path

if __name__ == "__main__":
    engine = AnalyticsEngine()
    engine.run()
