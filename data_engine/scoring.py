import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = Path("processed_data")

class ScoringEngine:
    def __init__(self, data_dir=PROCESSED_DATA_DIR):
        self.data_dir = data_dir
        
    def normalize(self, df, cols):
        """
        Min-Max Normalization
        """
        normalized = df.copy()
        for col in cols:
            if col in df.columns:
                min_val = df[col].min()
                max_val = df[col].max()
                if max_val - min_val > 0:
                    normalized[f'{col}_norm'] = (df[col] - min_val) / (max_val - min_val)
                else:
                    normalized[f'{col}_norm'] = 0
        return normalized

    def calculate_entropy_weights(self, df, cols):
        """
        Calculate entropy weights for the given columns.
        """
        # 1. Normalize matrix (using sum normalization for entropy)
        # Add small epsilon to avoid log(0)
        epsilon = 1e-9
        matrix = df[cols].values + epsilon
        
        # 2. Calculate probability matrix P
        P = matrix / matrix.sum(axis=0)
        
        # 3. Calculate Entropy E
        k = 1 / np.log(len(df))
        E = -k * (P * np.log(P)).sum(axis=0)
        
        # 4. Calculate Diversity D
        D = 1 - E
        
        # 5. Calculate Weights W
        W = D / D.sum()
        
        weights = dict(zip(cols, W))
        return weights

    def compute_scores(self, input_file="wards_with_indicators.geojson"):
        import geopandas as gpd
        
        logger.info("Loading data for scoring...")
        gdf = gpd.read_file(self.data_dir / input_file)
        
        # Define domains and their indicators
        domains = {
            'ACCESS': ['school_count_density', 'health_count_density', 'transit_count_density'],
            'OPPORTUNITY': ['commercial_count_density', 'fps_count_density'],
            'ENVIRONMENT': ['park_count_density', 'noise_level'], # noise should be inverted? Yes.
            'GOVERNANCE': ['sabha_count_density'] # Add more if available
        }
        
        # Invert negative indicators (like noise)
        # Assuming noise_level is higher = worse.
        # Min-Max norm for negative: (max - x) / (max - min)
        # Or just invert value before norm?
        # Let's handle it in normalization or pre-processing.
        if 'noise_level' in gdf.columns:
            gdf['noise_level_inv'] = gdf['noise_level'].max() - gdf['noise_level']
            domains['ENVIRONMENT'] = ['park_count_density', 'noise_level_inv']

        all_indicators = [ind for inds in domains.values() for ind in inds]
        
        # Normalize all indicators (Min-Max for scoring)
        gdf = self.normalize(gdf, all_indicators)
        
        # Calculate Domain Scores
        domain_scores = {}
        domain_weights = {}
        
        for domain, indicators in domains.items():
            norm_cols = [f'{ind}_norm' for ind in indicators if f'{ind}_norm' in gdf.columns]
            if not norm_cols:
                logger.warning(f"No indicators found for domain {domain}")
                gdf[f'{domain}_SCORE'] = 0
                continue
                
            # Calculate Entropy Weights
            weights = self.calculate_entropy_weights(gdf, norm_cols)
            domain_weights[domain] = weights
            
            # Weighted Sum
            score = np.zeros(len(gdf))
            for col, weight in weights.items():
                score += gdf[col] * weight
            
            gdf[f'{domain}_SCORE'] = score
            
        # Calculate Composite UEI Score (Average of Domain Scores for now, or Entropy again?)
        # Let's use equal weights for domains for simplicity, or entropy across domains.
        # User asked for "Compute composite UEI Score per ward".
        # Let's use equal weights for domains.
        gdf['UEI_SCORE'] = gdf[[f'{d}_SCORE' for d in domains.keys()]].mean(axis=1)
        
        # Save results
        output_path = self.data_dir / "ward_scores.geojson"
        gdf.to_file(output_path, driver='GeoJSON')
        
        # Save CSV
        gdf.drop(columns='geometry').to_csv(self.data_dir / "ward_scores.csv", index=False)
        
        # Save Weights
        weights_df = pd.DataFrame(domain_weights).T
        weights_df.to_csv(self.data_dir / "domain_entropy_weights.csv")
        
        logger.info(f"Scores computed and saved to {output_path}")
        return output_path

if __name__ == "__main__":
    engine = ScoringEngine()
    engine.compute_scores()
