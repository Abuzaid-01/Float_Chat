import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from database.models import Base

load_dotenv()

class DatabaseSetup:
    def __init__(self):
        # Try Streamlit secrets first, then fall back to environment variable
        self.database_url = None
        
        try:
            import streamlit as st
            # Streamlit secrets can be accessed like a dictionary
            if "DATABASE_URL" in st.secrets:
                self.database_url = st.secrets["DATABASE_URL"]
                print(f"✅ DATABASE_URL loaded from Streamlit secrets")
            else:
                print(f"⚠️ DATABASE_URL not found in Streamlit secrets. Available keys: {list(st.secrets.keys())}")
        except ImportError:
            print("ℹ️ Streamlit not available, using environment variable")
        except FileNotFoundError:
            print("⚠️ Streamlit secrets file not found")
        except Exception as e:
            print(f"⚠️ Error reading Streamlit secrets: {e}")
        
        # Fall back to environment variable if not in Streamlit secrets
        if not self.database_url:
            self.database_url = os.getenv('DATABASE_URL')
            if self.database_url:
                print(f"✅ DATABASE_URL loaded from environment variable")
        
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL not found in environment variables or Streamlit secrets. "
                "Please add DATABASE_URL to Streamlit Cloud Settings → Secrets"
            )
        
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
        print("✅ Database tables created successfully")
    
    def drop_tables(self):
        """Drop all tables (use with caution)"""
        Base.metadata.drop_all(bind=self.engine)
        print("⚠️ All tables dropped")
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                print("✅ Database connection successful")
                return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

# Usage
if __name__ == "__main__":
    db = DatabaseSetup()
    db.test_connection()
    db.create_tables()
