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


class SavedQuery(Base):
    """User saved queries and favorites"""
    __tablename__ = 'saved_queries'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Query info
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50))  # 'basic', 'mcp', 'spatial', etc.
    generated_sql = Column(Text)
    
    # User metadata
    user_id = Column(String(100))  # For multi-user in future
    query_name = Column(String(255))  # User-friendly name
    description = Column(Text)
    
    # Categorization
    is_favorite = Column(Integer, default=0)  # 0=normal, 1=favorite
    category = Column(String(50))  # 'temperature', 'salinity', 'spatial', etc.
    tags = Column(Text)  # JSON array of tags
    
    # Usage stats
    execution_count = Column(Integer, default=0)
    last_executed = Column(DateTime)
    
    # Results metadata
    result_count = Column(Integer)
    execution_time = Column(Float)
    
    # MCP info
    mcp_tools_used = Column(Text)  # JSON array
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # Sharing
    is_public = Column(Integer, default=0)  # 0=private, 1=public
    share_token = Column(String(100))  # For sharing links


class WorkflowRecipe(Base):
    """Pre-built analysis workflows"""
    __tablename__ = 'workflow_recipes'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Recipe info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # 'temperature', 'comparison', 'advanced'
    difficulty = Column(String(20))  # 'beginner', 'intermediate', 'advanced'
    
    # Steps (JSON)
    steps = Column(Text)  # JSON array of steps
    
    # Expected outcome
    expected_result = Column(Text)
    estimated_time = Column(String(50))  # "2 minutes"
    
    # Usage
    usage_count = Column(Integer, default=0)
    rating = Column(Float)  # Average user rating
    
    # Metadata
    icon = Column(String(50))  # Emoji or icon name
    tags = Column(Text)  # JSON array
    is_featured = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
