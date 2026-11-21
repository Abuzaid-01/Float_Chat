import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from database.models import Base

load_dotenv()

class DatabaseSetup:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            try:
                import streamlit as st

                self.database_url = st.secrets.get("DATABASE_URL")
            except (ImportError, FileNotFoundError):
                pass
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL not found in environment variables or Streamlit secrets. "
                "Please add DATABASE_URL to Streamlit Cloud Settings → Secrets"
            )
        
        url = make_url(self.database_url)
        # Use the installed driver for standard Neon URLs across SQLAlchemy versions.
        if url.drivername == "postgresql":
            url = url.set(drivername="postgresql+psycopg2")
        connect_args = {"connect_timeout": 5} if url.get_backend_name() == "postgresql" else {}
        self.engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
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
