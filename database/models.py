from sqlalchemy import Column, Integer, Float, String, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ArgoProfile(Base):
    """ARGO float profile data model"""
    __tablename__ = 'argo_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    float_id = Column(String(50), nullable=True)
    cycle_number = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    pressure = Column(Float, nullable=False)
    temperature = Column(Float, nullable=True)
    salinity = Column(Float, nullable=True)
    
    # BGC parameters (optional)
    dissolved_oxygen = Column(Float, nullable=True)
    chlorophyll = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    
    # Quality flags
    temp_qc = Column(Integer, nullable=True)
    sal_qc = Column(Integer, nullable=True)
    
    # Metadata
    data_mode = Column(String(1), nullable=True)
    platform_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Create indexes for efficient querying with schema specification
    __table_args__ = (
        Index('idx_lat_lon', 'latitude', 'longitude'),
        Index('idx_timestamp', 'timestamp'),
        Index('idx_float_id', 'float_id'),
        Index('idx_spatial_temporal', 'latitude', 'longitude', 'timestamp'),
        {'schema': 'public'}
    )

class ProfileSummary(Base):
    """Profile summaries for vector search"""
    __tablename__ = 'profile_summaries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    float_id = Column(String(50), nullable=True)
    cycle_number = Column(Integer, nullable=True)
    summary_text = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    min_depth = Column(Float)
    max_depth = Column(Float)
    temp_range = Column(String(50))
    sal_range = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_summary_location', 'latitude', 'longitude'),
        {'schema': 'public'}
    )

class QueryLog(Base):
    """Log user queries for analysis"""
    __tablename__ = 'query_logs'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_query = Column(Text, nullable=False)
    generated_sql = Column(Text)
    result_count = Column(Integer)
    execution_time = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Integer, default=1)
