"""
NetCDF Exporter for ARGO Data
Converts query results back to CF-compliant NetCDF format
Required by problem statement for data export
"""

import netCDF4 as nc
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class NetCDFExporter:
    """
    Export ARGO data to CF-compliant NetCDF format
    Follows ARGO data format specifications
    """
    
    def __init__(self):
        self.cf_conventions = "CF-1.6"
        self.argo_format_version = "3.1"
    
    # def export_to_netcdf(
    #     self,
    #     df: pd.DataFrame,
    #     output_path: str,
    #     metadata: Optional[Dict] = None
    # ) -> bool:
    #     """
    #     Export DataFrame to NetCDF file
        
    #     Args:
    #         df: DataFrame with ARGO data
    #         output_path: Output file path
    #         metadata: Additional metadata
            
    #     Returns:
    #         True if successful
    #     """
    #     try:
    #         logger.info(f"📦 Exporting {len(df)} records to NetCDF...")
            
    #         # Prepare output directory
    #         output_path = Path(output_path)
    #         output_path.parent.mkdir(parents=True, exist_ok=True)
            
    #         # Create NetCDF file
    #         with nc.Dataset(output_path, 'w', format='NETCDF4') as ncfile:
                
    #             # Add global attributes
    #             self._add_global_attributes(ncfile, df, metadata)
                
    #             # Create dimensions
    #             self._create_dimensions(ncfile, df)
                
    #             # Create variables
    #             self._create_variables(ncfile, df)
                
    #             # Write data
    #             self._write_data(ncfile, df)
            
    #         file_size = output_path.stat().st_size / (1024 * 1024)
    #         logger.info(f"✅ NetCDF export complete: {output_path} ({file_size:.2f} MB)")
            
    #         return True
            
    #     except Exception as e:
    #         logger.error(f"❌ NetCDF export failed: {e}")
    #         return False
    def export_to_netcdf(
        self,
        df: pd.DataFrame,
        output_path: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        IMPROVED: Export DataFrame to NetCDF file with better error handling
        and validation
        
        Args:
            df: DataFrame with ARGO data
            output_path: Output file path
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"📦 Starting NetCDF export of {len(df)} records...")
            
            # STEP 1: Validate input data
            validation_result = self._validate_input_data(df)
            if not validation_result['valid']:
                logger.error(f"❌ Data validation failed: {validation_result['errors']}")
                return False
            
            # STEP 2: Prepare output directory
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # STEP 3: Clean and prepare data
            df_clean = self._prepare_data_for_export(df)
            
            # STEP 4: Create NetCDF file
            logger.info(f"📝 Creating NetCDF file: {output_path}")
            with nc.Dataset(output_path, 'w', format='NETCDF4') as ncfile:
                
                # Add global attributes
                self._add_global_attributes(ncfile, df_clean, metadata)
                
                # Create dimensions
                self._create_dimensions(ncfile, df_clean)
                
                # Create variables
                self._create_variables(ncfile, df_clean)
                
                # Write data
                self._write_data(ncfile, df_clean)
                
                # Add quality control attributes
                self._add_qc_attributes(ncfile)
            
            # STEP 5: Verify the created file
            verification = self._verify_netcdf_file(output_path)
            if not verification['valid']:
                logger.error(f"❌ File verification failed: {verification['errors']}")
                return False
            
            file_size = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ NetCDF export complete: {output_path.name} ({file_size:.2f} MB)")
            logger.info(f"✅ Verification: {verification['message']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ NetCDF export failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _validate_input_data(self, df: pd.DataFrame) -> Dict:
        """Validate input DataFrame for NetCDF export"""
        
        errors = []
        warnings = []
        
        # Check if DataFrame is empty
        if df.empty:
            errors.append("DataFrame is empty")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Check required columns
        required_cols = ['latitude', 'longitude', 'pressure']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
        
        # Check for recommended columns
        recommended_cols = ['temperature', 'salinity', 'timestamp']
        missing_recommended = [col for col in recommended_cols if col not in df.columns]
        if missing_recommended:
            warnings.append(f"Missing recommended columns: {missing_recommended}")
        
        # Check data ranges
        if 'latitude' in df.columns:
            if df['latitude'].min() < -90 or df['latitude'].max() > 90:
                errors.append("Latitude values out of valid range (-90 to 90)")
        
        if 'longitude' in df.columns:
            if df['longitude'].min() < -180 or df['longitude'].max() > 180:
                errors.append("Longitude values out of valid range (-180 to 180)")
        
        if 'temperature' in df.columns:
            if df['temperature'].min() < -5 or df['temperature'].max() > 40:
                warnings.append("Temperature values outside typical ocean range")
        
        if 'salinity' in df.columns:
            if df['salinity'].min() < 0 or df['salinity'].max() > 42:
                warnings.append("Salinity values outside typical ocean range")
        
        # Check for NaN values
        nan_counts = df.isnull().sum()
        if nan_counts.any():
            warnings.append(f"Columns with NaN values: {nan_counts[nan_counts > 0].to_dict()}")
        
        valid = len(errors) == 0
        
        return {
            'valid': valid,
            'errors': errors,
            'warnings': warnings
        }
    
    def _prepare_data_for_export(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data for NetCDF export"""
        
        df_clean = df.copy()
        
        # Convert timestamp to datetime if needed
        if 'timestamp' in df_clean.columns:
            df_clean['timestamp'] = pd.to_datetime(df_clean['timestamp'], errors='coerce')
        
        # Clean float_id (remove byte string formatting if present)
        if 'float_id' in df_clean.columns:
            df_clean['float_id'] = df_clean['float_id'].astype(str).str.strip("b'\" ")
        
        # Fill NaN values with appropriate fill values
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            df_clean[col] = df_clean[col].fillna(99999.0)
        
        # Sort by float, cycle, and pressure
        sort_cols = []
        if 'float_id' in df_clean.columns:
            sort_cols.append('float_id')
        if 'cycle_number' in df_clean.columns:
            sort_cols.append('cycle_number')
        if 'pressure' in df_clean.columns:
            sort_cols.append('pressure')
        
        if sort_cols:
            df_clean = df_clean.sort_values(sort_cols)
        
        logger.info(f"✅ Data prepared: {len(df_clean)} records cleaned and sorted")
        
        return df_clean
    
    def _add_qc_attributes(self, ncfile: nc.Dataset):
        """Add quality control attributes to NetCDF file"""
        
        ncfile.quality_control_indicator = "ARGO QC flags: 1=good, 2=probably good, 3=questionable, 4=bad, 9=missing"
        ncfile.quality_control_conventions = "ARGO quality control manual"
        ncfile.quality_control_date = datetime.now().isoformat()
    
    def _verify_netcdf_file(self, file_path: Path) -> Dict:
        """Verify the created NetCDF file"""
        
        try:
            with nc.Dataset(file_path, 'r') as ncfile:
                # Check dimensions
                if 'N_PROF' not in ncfile.dimensions:
                    return {
                        'valid': False,
                        'errors': ['Missing N_PROF dimension']
                    }
                
                # Check required variables
                required_vars = ['LATITUDE', 'LONGITUDE', 'PRES']
                missing_vars = [v for v in required_vars if v not in ncfile.variables]
                if missing_vars:
                    return {
                        'valid': False,
                        'errors': [f'Missing required variables: {missing_vars}']
                    }
                
                # Check CF compliance
                if not hasattr(ncfile, 'Conventions'):
                    return {
                        'valid': False,
                        'errors': ['Missing CF Conventions attribute']
                    }
                
                # All checks passed
                n_prof = ncfile.dimensions['N_PROF'].size
                n_levels = ncfile.dimensions['N_LEVELS'].size if 'N_LEVELS' in ncfile.dimensions else 0
                
                return {
                    'valid': True,
                    'message': f'Valid ARGO NetCDF file: {n_prof} profiles, {n_levels} levels',
                    'errors': []
                }
        
        except Exception as e:
            return {
                'valid': False,
                'errors': [f'Verification error: {str(e)}']
            }
    def _add_global_attributes(
        self,
        ncfile: nc.Dataset,
        df: pd.DataFrame,
        metadata: Optional[Dict]
    ):
        """Add CF-compliant global attributes"""
        
        ncfile.Conventions = self.cf_conventions
        ncfile.title = "ARGO Float Data - FloatChat Export"
        ncfile.institution = "Indian National Centre for Ocean Information Services (INCOIS)"
        ncfile.source = "ARGO profiling floats"
        ncfile.history = f"Created on {datetime.now().isoformat()} by FloatChat"
        ncfile.references = "http://www.argodatamgt.org/"
        ncfile.comment = "Data exported from FloatChat ARGO database"
        
        # Data coverage
        ncfile.geospatial_lat_min = float(df['latitude'].min())
        ncfile.geospatial_lat_max = float(df['latitude'].max())
        ncfile.geospatial_lon_min = float(df['longitude'].min())
        ncfile.geospatial_lon_max = float(df['longitude'].max())
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            ncfile.time_coverage_start = df['timestamp'].min().isoformat()
            ncfile.time_coverage_end = df['timestamp'].max().isoformat()
        
        # ARGO specific
        ncfile.format_version = self.argo_format_version
        ncfile.data_type = "ARGO profile"
        
        # FloatChat specific
        ncfile.processing_software = "FloatChat v2.0"
        ncfile.processing_date = datetime.now().isoformat()
        
        # Add custom metadata
        if metadata:
            for key, value in metadata.items():
                setattr(ncfile, key, str(value))
    
    def _create_dimensions(self, ncfile: nc.Dataset, df: pd.DataFrame):
        """Create NetCDF dimensions"""
        
        # Determine unique profiles
        if 'float_id' in df.columns and 'cycle_number' in df.columns:
            n_prof = df.groupby(['float_id', 'cycle_number']).ngroups
        else:
            n_prof = 1
        
        # Get maximum levels per profile
        if 'pressure' in df.columns:
            n_levels = df.groupby(['float_id', 'cycle_number'])['pressure'].count().max()
        else:
            n_levels = len(df)
        
        # Create dimensions
        ncfile.createDimension('N_PROF', n_prof)
        ncfile.createDimension('N_LEVELS', n_levels)
        ncfile.createDimension('STRING256', 256)
        
        logger.info(f"   Dimensions: N_PROF={n_prof}, N_LEVELS={n_levels}")
    
    def _create_variables(self, ncfile: nc.Dataset, df: pd.DataFrame):
        """Create NetCDF variables with CF attributes"""
        
        # Position variables
        lat = ncfile.createVariable('LATITUDE', 'f4', ('N_PROF',), 
                                     fill_value=99999.0)
        lat.long_name = "Latitude of the station"
        lat.standard_name = "latitude"
        lat.units = "degrees_north"
        lat.valid_min = -90.0
        lat.valid_max = 90.0
        lat.axis = "Y"
        
        lon = ncfile.createVariable('LONGITUDE', 'f4', ('N_PROF',),
                                     fill_value=99999.0)
        lon.long_name = "Longitude of the station"
        lon.standard_name = "longitude"
        lon.units = "degrees_east"
        lon.valid_min = -180.0
        lon.valid_max = 180.0
        lon.axis = "X"
        
        # Time variable (ARGO uses Julian days since 1950-01-01)
        juld = ncfile.createVariable('JULD', 'f8', ('N_PROF',),
                                      fill_value=999999.0)
        juld.long_name = "Julian day (UTC) of the station"
        juld.standard_name = "time"
        juld.units = "days since 1950-01-01 00:00:00 UTC"
        juld.conventions = "Relative julian days with decimal part"
        juld.axis = "T"
        
        # Pressure (depth)
        pres = ncfile.createVariable('PRES', 'f4', ('N_PROF', 'N_LEVELS'),
                                      fill_value=99999.0)
        pres.long_name = "Sea water pressure"
        pres.standard_name = "sea_water_pressure"
        pres.units = "decibar"
        pres.valid_min = 0.0
        pres.valid_max = 12000.0
        pres.C_format = "%.3f"
        pres.FORTRAN_format = "F.3"
        pres.resolution = 0.001
        pres.axis = "Z"
        
        # Temperature
        temp = ncfile.createVariable('TEMP', 'f4', ('N_PROF', 'N_LEVELS'),
                                      fill_value=99999.0)
        temp.long_name = "Sea water temperature"
        temp.standard_name = "sea_water_temperature"
        temp.units = "degree_Celsius"
        temp.valid_min = -2.5
        temp.valid_max = 40.0
        temp.C_format = "%.3f"
        temp.FORTRAN_format = "F.3"
        temp.resolution = 0.001
        
        # Salinity
        psal = ncfile.createVariable('PSAL', 'f4', ('N_PROF', 'N_LEVELS'),
                                      fill_value=99999.0)
        psal.long_name = "Practical salinity"
        psal.standard_name = "sea_water_practical_salinity"
        psal.units = "psu"
        psal.valid_min = 2.0
        psal.valid_max = 41.0
        psal.C_format = "%.3f"
        psal.FORTRAN_format = "F.3"
        psal.resolution = 0.001
        
        # Quality control flags
        temp_qc = ncfile.createVariable('TEMP_QC', 'i1', ('N_PROF', 'N_LEVELS'),
                                         fill_value=9)
        temp_qc.long_name = "Quality flag for TEMP"
        temp_qc.conventions = "ARGO quality flag"
        temp_qc.flag_values = np.array([0, 1, 2, 3, 4, 5, 8, 9], dtype=np.int8)
        temp_qc.flag_meanings = "no_qc good probably_good questionable bad value_changed interpolated missing_value"
        
        psal_qc = ncfile.createVariable('PSAL_QC', 'i1', ('N_PROF', 'N_LEVELS'),
                                         fill_value=9)
        psal_qc.long_name = "Quality flag for PSAL"
        psal_qc.conventions = "ARGO quality flag"
        psal_qc.flag_values = np.array([0, 1, 2, 3, 4, 5, 8, 9], dtype=np.int8)
        psal_qc.flag_meanings = "no_qc good probably_good questionable bad value_changed interpolated missing_value"
        
        # BGC parameters (if available)
        if 'dissolved_oxygen' in df.columns:
            doxy = ncfile.createVariable('DOXY', 'f4', ('N_PROF', 'N_LEVELS'),
                                          fill_value=99999.0)
            doxy.long_name = "Dissolved oxygen"
            doxy.standard_name = "moles_of_oxygen_per_unit_mass_in_sea_water"
            doxy.units = "micromole/kg"
            doxy.valid_min = 0.0
            doxy.valid_max = 600.0
            doxy.C_format = "%.3f"
            doxy.resolution = 0.001
        
        if 'chlorophyll' in df.columns:
            chla = ncfile.createVariable('CHLA', 'f4', ('N_PROF', 'N_LEVELS'),
                                          fill_value=99999.0)
            chla.long_name = "Chlorophyll-A"
            chla.standard_name = "mass_concentration_of_chlorophyll_a_in_sea_water"
            chla.units = "mg/m3"
            chla.valid_min = 0.0
            chla.valid_max = 100.0
            chla.C_format = "%.4f"
            chla.resolution = 0.0001
        
        if 'ph' in df.columns:
            ph_var = ncfile.createVariable('PH_IN_SITU_TOTAL', 'f4', ('N_PROF', 'N_LEVELS'),
                                            fill_value=99999.0)
            ph_var.long_name = "pH"
            ph_var.standard_name = "sea_water_ph_reported_on_total_scale"
            ph_var.units = "dimensionless"
            ph_var.valid_min = 6.5
            ph_var.valid_max = 9.0
            ph_var.C_format = "%.4f"
            ph_var.resolution = 0.0001
        
        # Float identification
        platform_number = ncfile.createVariable('PLATFORM_NUMBER', 'S1',
                                                 ('N_PROF', 'STRING256'))
        platform_number.long_name = "Float unique identifier"
        platform_number.conventions = "WMO float identifier : A9IIIII"
        
        cycle_number = ncfile.createVariable('CYCLE_NUMBER', 'i4', ('N_PROF',),
                                              fill_value=99999)
        cycle_number.long_name = "Float cycle number"
        cycle_number.conventions = "0..N, 0 : launch cycle, 1 : first complete cycle"
        
        # Data mode
        data_mode = ncfile.createVariable('DATA_MODE', 'S1', ('N_PROF',))
        data_mode.long_name = "Delayed mode or real time data"
        data_mode.conventions = "R : real time; D : delayed mode; A : real time with adjustment"
        
        logger.info(f"   Variables created: {len(ncfile.variables)}")
    
    def _write_data(self, ncfile: nc.Dataset, df: pd.DataFrame):
        """Write data to NetCDF variables"""
        
        # Group by profile
        if 'float_id' in df.columns and 'cycle_number' in df.columns:
            profiles = df.groupby(['float_id', 'cycle_number'])
        else:
            profiles = [(None, df)]
        
        for prof_idx, (profile_id, profile_data) in enumerate(profiles):
            
            # Sort by pressure (depth)
            profile_data = profile_data.sort_values('pressure')
            
            # Write position
            ncfile.variables['LATITUDE'][prof_idx] = profile_data['latitude'].iloc[0]
            ncfile.variables['LONGITUDE'][prof_idx] = profile_data['longitude'].iloc[0]
            
            # Write time (convert to Julian days since 1950-01-01)
            if 'timestamp' in profile_data.columns:
                timestamp = pd.to_datetime(profile_data['timestamp'].iloc[0])
                reference = pd.Timestamp('1950-01-01')
                julian_days = (timestamp - reference).total_seconds() / 86400.0
                ncfile.variables['JULD'][prof_idx] = julian_days
            
            # Write profile data
            n_levels = len(profile_data)
            
            if 'pressure' in profile_data.columns:
                ncfile.variables['PRES'][prof_idx, :n_levels] = profile_data['pressure'].values
            
            if 'temperature' in profile_data.columns:
                ncfile.variables['TEMP'][prof_idx, :n_levels] = profile_data['temperature'].values
            
            if 'salinity' in profile_data.columns:
                ncfile.variables['PSAL'][prof_idx, :n_levels] = profile_data['salinity'].values
            
            # Write QC flags
            if 'temp_qc' in profile_data.columns:
                ncfile.variables['TEMP_QC'][prof_idx, :n_levels] = profile_data['temp_qc'].values
            
            if 'sal_qc' in profile_data.columns:
                ncfile.variables['PSAL_QC'][prof_idx, :n_levels] = profile_data['sal_qc'].values
            
            # Write BGC parameters
            if 'dissolved_oxygen' in profile_data.columns and 'DOXY' in ncfile.variables:
                ncfile.variables['DOXY'][prof_idx, :n_levels] = profile_data['dissolved_oxygen'].values
            
            if 'chlorophyll' in profile_data.columns and 'CHLA' in ncfile.variables:
                ncfile.variables['CHLA'][prof_idx, :n_levels] = profile_data['chlorophyll'].values
            
            if 'ph' in profile_data.columns and 'PH_IN_SITU_TOTAL' in ncfile.variables:
                ncfile.variables['PH_IN_SITU_TOTAL'][prof_idx, :n_levels] = profile_data['ph'].values
            
            # Write float ID
            if profile_id and profile_id[0]:
                float_id_str = str(profile_id[0]).strip("b' ")
                float_id_array = np.array(list(float_id_str.ljust(256)), dtype='S1')
                ncfile.variables['PLATFORM_NUMBER'][prof_idx] = float_id_array
                
                # Write cycle number
                ncfile.variables['CYCLE_NUMBER'][prof_idx] = profile_id[1]
            
            # Write data mode
            if 'data_mode' in profile_data.columns:
                data_mode_val = profile_data['data_mode'].iloc[0]
                ncfile.variables['DATA_MODE'][prof_idx] = data_mode_val
        
        logger.info(f"   Data written: {prof_idx + 1} profiles")


    def export_with_progress(
        self,
        df: pd.DataFrame,
        output_path: str,
        metadata: Optional[Dict] = None,
        progress_callback=None
    ) -> Dict:
        """
        Export with progress reporting for Streamlit
        
        Returns:
            Dict with status, message, and file info
        """
        
        result = {
            'success': False,
            'message': '',
            'file_path': None,
            'file_size_mb': 0,
            'records_exported': 0
        }
        
        try:
            if progress_callback:
                progress_callback(0.1, "Validating data...")
            
            # Validate
            validation = self._validate_input_data(df)
            if not validation['valid']:
                result['message'] = f"Validation failed: {validation['errors']}"
                return result
            
            if progress_callback:
                progress_callback(0.3, "Preparing data...")
            
            # Prepare
            df_clean = self._prepare_data_for_export(df)
            
            if progress_callback:
                progress_callback(0.5, "Creating NetCDF file...")
            
            # Export
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with nc.Dataset(output_path, 'w', format='NETCDF4') as ncfile:
                self._add_global_attributes(ncfile, df_clean, metadata)
                
                if progress_callback:
                    progress_callback(0.6, "Writing dimensions...")
                
                self._create_dimensions(ncfile, df_clean)
                
                if progress_callback:
                    progress_callback(0.7, "Writing variables...")
                
                self._create_variables(ncfile, df_clean)
                
                if progress_callback:
                    progress_callback(0.8, "Writing data...")
                
                self._write_data(ncfile, df_clean)
                self._add_qc_attributes(ncfile)
            
            if progress_callback:
                progress_callback(0.9, "Verifying file...")
            
            # Verify
            verification = self._verify_netcdf_file(output_path)
            
            if progress_callback:
                progress_callback(1.0, "Complete!")
            
            if verification['valid']:
                file_size = output_path.stat().st_size / (1024 * 1024)
                result['success'] = True
                result['message'] = f"Successfully exported {len(df_clean)} records"
                result['file_path'] = str(output_path)
                result['file_size_mb'] = file_size
                result['records_exported'] = len(df_clean)
            else:
                result['message'] = f"Export succeeded but verification failed: {verification['errors']}"
            
            return result
            
        except Exception as e:
            result['message'] = f"Export error: {str(e)}"
            logger.error(f"Export with progress failed: {e}")
            return result    
    
    def export_to_ascii(
        self,
        df: pd.DataFrame,
        output_path: str,
        format_type: str = 'csv'
    ) -> bool:
        """
        Export to ASCII format (CSV or custom ARGO ASCII)
        
        Args:
            df: DataFrame with ARGO data
            output_path: Output file path
            format_type: 'csv' or 'argo_ascii'
            
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type == 'csv':
                df.to_csv(output_path, index=False)
                logger.info(f"✅ CSV export: {output_path}")
                
            elif format_type == 'argo_ascii':
                self._write_argo_ascii(df, output_path)
                logger.info(f"✅ ARGO ASCII export: {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ ASCII export failed: {e}")
            return False
    
    def _write_argo_ascii(self, df: pd.DataFrame, output_path: Path):
        """Write ARGO-specific ASCII format"""
        
        with open(output_path, 'w') as f:
            # Write header
            f.write("# ARGO Float Data - FloatChat Export\n")
            f.write(f"# Export Date: {datetime.now().isoformat()}\n")
            f.write(f"# Total Profiles: {df.groupby(['float_id', 'cycle_number']).ngroups}\n")
            f.write(f"# Total Measurements: {len(df)}\n")
            f.write("#\n")
            f.write("# Column Format:\n")
            f.write("# FLOAT_ID CYCLE LAT LON DATE_TIME PRES TEMP PSAL TEMP_QC PSAL_QC\n")
            f.write("#" + "="*80 + "\n")
            
            # Write data
            for _, row in df.iterrows():
                float_id = str(row.get('float_id', 'NA')).strip("b' ")
                cycle = row.get('cycle_number', 0)
                lat = row.get('latitude', 999.999)
                lon = row.get('longitude', 999.999)
                timestamp = row.get('timestamp', 'NA')
                pres = row.get('pressure', 99999.0)
                temp = row.get('temperature', 99999.0)
                psal = row.get('salinity', 99999.0)
                temp_qc = row.get('temp_qc', 9)
                psal_qc = row.get('sal_qc', 9)
                
                f.write(f"{float_id:>10s} {cycle:>5d} {lat:>8.3f} {lon:>9.3f} "
                       f"{str(timestamp):>20s} {pres:>8.2f} {temp:>7.3f} "
                       f"{psal:>7.3f} {temp_qc:>2d} {psal_qc:>2d}\n")
    
    def validate_netcdf(self, file_path: str) -> Dict:
        """
        Validate exported NetCDF file
        
        Returns dict with validation results
        """
        try:
            with nc.Dataset(file_path, 'r') as ncfile:
                validation = {
                    'valid': True,
                    'cf_compliant': self.cf_conventions in ncfile.Conventions,
                    'dimensions': dict(ncfile.dimensions.items()),
                    'variables': list(ncfile.variables.keys()),
                    'global_attributes': {k: getattr(ncfile, k) for k in ncfile.ncattrs()},
                    'file_size_mb': Path(file_path).stat().st_size / (1024 * 1024)
                }
                
                # Check required variables
                required_vars = ['LATITUDE', 'LONGITUDE', 'JULD', 'PRES', 'TEMP', 'PSAL']
                missing = [v for v in required_vars if v not in validation['variables']]
                
                if missing:
                    validation['valid'] = False
                    validation['missing_variables'] = missing
                
                return validation
                
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }


# Convenience functions
def export_dataframe_to_netcdf(
    df: pd.DataFrame,
    output_path: str,
    metadata: Optional[Dict] = None
) -> bool:
    """Quick export function"""
    exporter = NetCDFExporter()
    return exporter.export_to_netcdf(df, output_path, metadata)


def export_dataframe_to_ascii(
    df: pd.DataFrame,
    output_path: str,
    format_type: str = 'csv'
) -> bool:
    """Quick ASCII export function"""
    exporter = NetCDFExporter()
    return exporter.export_to_ascii(df, output_path, format_type)


# Example usage
if __name__ == "__main__":
    # Test with sample data
    sample_df = pd.DataFrame({
        'float_id': ["b'6904092 '"] * 5,
        'cycle_number': [1] * 5,
        'latitude': [15.5] * 5,
        'longitude': [70.3] * 5,
        'timestamp': pd.date_range('2025-01-01', periods=5, freq='H'),
        'pressure': [10, 50, 100, 200, 500],
        'temperature': [28.5, 27.2, 25.8, 22.5, 18.2],
        'salinity': [34.5, 34.6, 34.8, 35.0, 35.2],
        'temp_qc': [1, 1, 1, 2, 2],
        'sal_qc': [1, 1, 1, 2, 2]
    })
    
    exporter = NetCDFExporter()
    success = exporter.export_to_netcdf(sample_df, 'test_export.nc')
    
    if success:
        validation = exporter.validate_netcdf('test_export.nc')
        print("Validation:", validation)