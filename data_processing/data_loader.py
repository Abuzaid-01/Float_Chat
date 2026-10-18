import pandas as pd
from sqlalchemy.orm import Session
from database.db_setup import DatabaseSetup
from database.models import ArgoProfile
from data_processing.regions import classify_ocean_region, normalize_float_id
from tqdm import tqdm

class DataLoader:
    """Load processed data into database"""
    
    def __init__(self):
        self.db_setup = DatabaseSetup()
    
    @staticmethod
    def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply FloatChat data conventions to a DataFrame before loading:
        - normalize float_id (strip numpy b'...' wrapper)
        - classify ocean_region from lat/lon
        """
        df = df.copy()

        # Rename 'time' column to 'timestamp' if it exists
        if 'time' in df.columns:
            df = df.rename(columns={'time': 'timestamp'})

        # Convert timestamp column to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ns', errors='coerce')

        # Normalize float_id so exact-match queries can use the index
        if 'float_id' in df.columns:
            df['float_id'] = df['float_id'].apply(normalize_float_id)

        # Classify ocean region from coordinates (kept in sync with the
        # SQL generator's region definitions and the MCP tools)
        if 'latitude' in df.columns and 'longitude' in df.columns:
            df['ocean_region'] = [
                classify_ocean_region(lat, lon)
                for lat, lon in zip(df['latitude'], df['longitude'])
            ]

        return df

    def load_csv_to_db(self, csv_path: str, batch_size: int = 1000):
        """Load CSV data into database in batches"""
        print(f"📊 Loading data from {csv_path}")
        df = pd.read_csv(csv_path)
        df = self.prepare_dataframe(df)
        
        session = self.db_setup.get_session()
        
        try:
            total_rows = len(df)
            for i in tqdm(range(0, total_rows, batch_size), desc="Loading batches"):
                batch = df.iloc[i:i+batch_size]
                
                # Create ArgoProfile objects
                profiles = [
                    ArgoProfile(**row.to_dict()) 
                    for _, row in batch.iterrows()
                ]
                
                session.bulk_save_objects(profiles)
                session.commit()
            
            print(f"✅ Successfully loaded {total_rows} records")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error loading data: {e}")
            import traceback
            traceback.print_exc()
        finally:
            session.close()
    
    def get_record_count(self) -> int:
        """Get total number of records in database"""
        session = self.db_setup.get_session()
        count = session.query(ArgoProfile).count()
        session.close()
        return count

# Usage
if __name__ == "__main__":
    loader = DataLoader()
    loader.load_csv_to_db("/Users/abuzaid/Desktop/final/netcdf/FloatChat/data/processed/argo_profiles.csv")
    print(f"Total records: {loader.get_record_count()}")
