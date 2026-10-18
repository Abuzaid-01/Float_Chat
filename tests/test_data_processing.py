import unittest
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from data_processing.netcdf_extractor import NetCDFExtractor
from data_processing.data_loader import DataLoader
import pandas as pd

class TestDataProcessing(unittest.TestCase):
    """Test data processing components"""
    
    def test_netcdf_extraction(self):
        """Test NetCDF file extraction"""
        # This would test with actual NetCDF file
        # For now, it's a placeholder
        print("Testing NetCDF extraction...")
        self.assertTrue(True)
    
    def test_csv_structure(self):
        """
        Test CSV has required columns after passing through the loader pipeline.
        The raw CSV uses 'time' (renamed to 'timestamp' by DataLoader) and the
        loader now classifies ocean_region from lat/lon.
        """
        required_columns = ['latitude', 'longitude', 'timestamp',
                          'pressure', 'temperature', 'salinity', 'ocean_region']
        
        # Load your CSV through the real pipeline step
        df = pd.read_csv('data/processed/argo_profiles.csv')
        df = DataLoader.prepare_dataframe(df)
        
        for col in required_columns:
            self.assertIn(col, df.columns, f"Missing column: {col}")
        
        # Every row with valid coordinates should get a region (or None if
        # outside the Indian Ocean — never an empty string)
        invalid_regions = df['ocean_region'].dropna()
        self.assertFalse((invalid_regions == '').any())
        
        print("✅ CSV structure test passed")
    
    def test_data_types(self):
        """Test data types are correct after pipeline preparation"""
        df = pd.read_csv('data/processed/argo_profiles.csv')
        df = DataLoader.prepare_dataframe(df)
        
        # Check numeric columns
        self.assertTrue(pd.api.types.is_numeric_dtype(df['latitude']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['longitude']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['temperature']))
        
        # timestamp must be datetime after the rename+parse step
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['timestamp']))
        
        print("✅ Data types test passed")

if __name__ == '__main__':
    unittest.main()
