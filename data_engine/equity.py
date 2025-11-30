import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calculate_gini(array):
    """
    Calculate the Gini coefficient of a numpy array.
    """
    # Based on bottom-up calculation
    array = np.array(array, dtype=np.float64)
    if np.amin(array) < 0:
        # Shift values so that min is 0
        array -= np.amin(array)
    
    # Values cannot be 0 for Gini? No, they can.
    # But if all are 0, Gini is 0.
    if np.sum(array) == 0:
        return 0
        
    array = np.sort(array)
    index = np.arange(1, array.shape[0] + 1)
    n = array.shape[0]
    
    return ((np.sum((2 * index - n - 1) * array)) / (n * np.sum(array)))

class EquityEngine:
    def __init__(self):
        pass
        
    def calculate_egalitarian(self, df, cols):
        """
        Calculates Gini index for each column.
        """
        gini_scores = {}
        for col in cols:
            if col in df.columns:
                gini_scores[col] = calculate_gini(df[col].values)
        return gini_scores
        
    def calculate_sufficientarian(self, df, type_cols, threshold=1):
        """
        Calculates sufficientarian scores.
        
        Args:
            df (DataFrame): Data.
            type_cols (list): List of columns representing counts of different types (e.g. ['school_15min', 'park_15min']).
            threshold (int): Minimum count to be considered "accessed" (default 1).
            
        Returns:
            Series: Score for each row (0 to 1).
        """
        # For each row, count how many types have value >= threshold
        # Score = (Number of types met) / (Total types)
        
        met_criteria = (df[type_cols] >= threshold).sum(axis=1)
        score = met_criteria / len(type_cols)
        return score
        
    def calculate_thematic_sufficiency(self, df, themes):
        """
        Calculates sufficiency scores for thematic groups.
        
        Args:
            df (DataFrame): Data.
            themes (dict): Dict of {theme_name: [col1, col2, ...]}.
            
        Returns:
            DataFrame: df with added theme score columns.
        """
        for theme, cols in themes.items():
            # Filter cols that exist
            valid_cols = [c for c in cols if c in df.columns]
            if not valid_cols:
                logger.warning(f"No columns found for theme {theme}")
                df[f'{theme}_sufficiency'] = 0
                continue
                
            # Logic: Access to AT LEAST ONE of the destinations in the theme?
            # Or access to ALL?
            # Paper says: 
            # "Mobility is defined as access to at least one metro, bus, or tram stop" -> OR logic within theme?
            # "Daily needs refer to access to a pharmacy and a supermarket" -> AND logic?
            
            # Let's implement based on paper description:
            # Mobility: OR (metro | bus | tram)
            # Leisure: OR (nightlife | culture | library | square | cafe)
            # Family: AND? "playground, kindergarten, and public square" -> The text says "includes access to...", table says "Playground, kindergarten, public square".
            # Wait, Table 2 says: "At least one of each destination type" for "All".
            # For themes, it lists types.
            # Let's assume "Sufficientarian" usually means "Access to X AND Y AND Z" if they are distinct needs.
            # But for Mobility (Bus vs Metro), they are substitutes.
            
            # Let's stick to the "Access to at least one of EACH type in the list" as the strict sufficiency,
            # OR "Access to ANY in the list" for substitutes.
            
            # Paper Table 2:
            # Mobility: "Metro, bus, or tram station" -> ANY
            # Leisure: "Nightlife, culture, library, public square, cafe/rest" -> ANY? Or ALL?
            # Text says: "leisure includes access to a nightlife venue, cultural place, library, public square, or cafe/restaurant" -> OR
            # Daily needs: "Pharmacy and a supermarket" -> AND
            # Family: "Playground, kindergarten, and public square" -> AND
            
            # I will implement a flexible "rules" system if needed, but for now:
            # I'll assume AND for distinct types, OR for substitutes.
            # But the input `themes` is just a list.
            
            # Let's simplify: Calculate the "Sufficientarian Score" as % of types accessed.
            # If the user wants "Mobility", I'll pass ['transit_15min'].
            # If "Daily Needs", I'll pass ['pharmacy_15min', 'supermarket_15min'].
            
            # Wait, the paper defines themes specifically.
            # I should probably just calculate the "General Sufficiency" (access to all essential types) first.
            
            df[f'{theme}_sufficiency'] = self.calculate_sufficientarian(df, valid_cols)
            
        return df
