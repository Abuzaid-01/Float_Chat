import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict
from datetime import datetime

class NetCDFExtractor:
    """Extract ARGO data from NetCDF files"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.ds = None
    
    def load_netcdf(self):
        """Load NetCDF file"""
        try:
            self.ds = xr.open_dataset(self.file_path)
            print(f"✅ Loaded NetCDF file: {self.file_path}")
            return True
        except Exception as e:
            print(f"❌ Error loading NetCDF: {e}")
            return False
    
    def extract_profiles(self) -> pd.DataFrame:
        """Extract all profiles from NetCDF file"""
        if self.ds is None:
            self.load_netcdf()
        
        profiles = []
        
        # Get dimensions
        n_prof = self.ds.dims.get('N_PROF', 1)
        n_levels = self.ds.dims.get('N_LEVELS', 0)
        
        for prof_idx in range(n_prof):
            # Extract profile metadata
            lat = float(self.ds['LATITUDE'].values[prof_idx])
            lon = float(self.ds['LONGITUDE'].values[prof_idx])
            juld = self.ds['JULD'].values[prof_idx]
            
            # Convert Julian date to datetime
            timestamp = self._julian_to_datetime(juld)
            
            # Get float ID and cycle number
            try:
                float_id = str(self.ds['PLATFORM_NUMBER'].values[prof_idx])
                cycle_num = int(self.ds['CYCLE_NUMBER'].values[prof_idx])
            except:
                float_id = None
                cycle_num = None
            
            # Extract profile data
            for level_idx in range(n_levels):
                pressure = self.ds['PRES'].values[prof_idx, level_idx]
                temp = self.ds['TEMP'].values[prof_idx, level_idx]
                sal = self.ds['PSAL'].values[prof_idx, level_idx]
                
                # Skip NaN values
                if np.isnan(pressure) or np.isnan(temp) or np.isnan(sal):
                    continue
                
                profile_data = {
                    'float_id': float_id,
                    'cycle_number': cycle_num,
                    'latitude': lat,
                    'longitude': lon,
                    'timestamp': timestamp,
                    'pressure': float(pressure),
                    'temperature': float(temp),
                    'salinity': float(sal)
                }
                
                # Add QC flags if available
                try:
                    profile_data['temp_qc'] = int(self.ds['TEMP_QC'].values[prof_idx, level_idx])
                    profile_data['sal_qc'] = int(self.ds['PSAL_QC'].values[prof_idx, level_idx])
                except:
                    pass
                
                profiles.append(profile_data)
        
        df = pd.DataFrame(profiles)
        print(f"✅ Extracted {len(df)} measurements from {n_prof} profiles")
        return df
    
    def _julian_to_datetime(self, julian_date):
        """Convert Julian date to datetime"""
        try:
            # Check if it's already a datetime object (numpy.datetime64)
            if hasattr(julian_date, 'dtype') and np.issubdtype(julian_date.dtype, np.datetime64):
                # Already a datetime, just convert to pandas Timestamp
                return pd.Timestamp(julian_date)
            
            # Check if it's a string that can be parsed
            if isinstance(julian_date, (str, bytes)):
                return pd.to_datetime(julian_date)
            
            # Otherwise, assume it's Julian days since 1950-01-01
            # ARGO uses days since 1950-01-01
            reference_date = pd.Timestamp('1950-01-01')
            return reference_date + pd.Timedelta(days=float(julian_date))
        except Exception as e:
            print(f"⚠️ Warning: Could not convert date: {e}")
            return pd.Timestamp('1950-01-01')
    
    def get_profile_summary(self) -> Dict:
        """Get summary statistics of the dataset"""
        if self.ds is None:
            self.load_netcdf()
        
        summary = {
            'n_profiles': self.ds.dims.get('N_PROF', 0),
            'n_levels': self.ds.dims.get('N_LEVELS', 0),
            'latitude_range': (
                float(self.ds['LATITUDE'].min().values),
                float(self.ds['LATITUDE'].max().values)
            ),
            'longitude_range': (
                float(self.ds['LONGITUDE'].min().values),
                float(self.ds['LONGITUDE'].max().values)
            ),
            'variables': list(self.ds.data_vars.keys())
        }
        return summary
    
    def close(self):
        """Close NetCDF file"""
        if self.ds is not None:
            self.ds.close()

# Usage example
if __name__ == "__main__":
    extractor = NetCDFExtractor("data/raw/argo_profile.nc")
    df = extractor.extract_profiles()
    df.to_csv("data/processed/argo_profiles.csv", index=False)
    print(extractor.get_profile_summary())
    extractor.close()

