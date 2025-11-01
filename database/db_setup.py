import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from database.models import Base

load_dotenv()

class DatabaseSetup:
    def __init__(self):
        # Try Streamlit secrets first, then fall back to environment variable
        try:
            import streamlit as st
            self.database_url = st.secrets.get("DATABASE_URL", os.getenv('DATABASE_URL'))
        except (ImportError, FileNotFoundError):
            # If not in Streamlit or secrets not found, use environment variable
            self.database_url = os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment variables or Streamlit secrets")
        
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
