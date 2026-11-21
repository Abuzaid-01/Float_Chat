from sqlalchemy import func

from data_processing.regions import classify_ocean_region
from database.db_setup import DatabaseSetup
from database.models import ArgoProfile, ProfileSummary

class ProfileSummarizer:
    """Generate natural language summaries of profiles"""
    
    def __init__(self):
        self.db_setup = DatabaseSetup()
    
    def generate_summaries(self):
        """Generate summaries for all profiles"""
        session = self.db_setup.get_session()
        
        # Group by float_id, cycle_number, timestamp
        profiles = session.query(
            ArgoProfile.float_id,
            ArgoProfile.cycle_number,
            ArgoProfile.latitude,
            ArgoProfile.longitude,
            ArgoProfile.timestamp,
            func.min(ArgoProfile.pressure).label('min_depth'),
            func.max(ArgoProfile.pressure).label('max_depth'),
            func.min(ArgoProfile.temperature).label('min_temp'),
            func.max(ArgoProfile.temperature).label('max_temp'),
            func.avg(ArgoProfile.temperature).label('avg_temp'),
            func.min(ArgoProfile.salinity).label('min_sal'),
            func.max(ArgoProfile.salinity).label('max_sal'),
            func.avg(ArgoProfile.salinity).label('avg_sal')
        ).group_by(
            ArgoProfile.float_id,
            ArgoProfile.cycle_number,
            ArgoProfile.latitude,
            ArgoProfile.longitude,
            ArgoProfile.timestamp
        ).all()
        
        summaries = []
        for prof in profiles:
            summary_text = self._create_summary_text(prof)
            
            summary = ProfileSummary(
                float_id=prof.float_id,
                cycle_number=prof.cycle_number,
                latitude=prof.latitude,
                longitude=prof.longitude,
                timestamp=prof.timestamp,
                min_depth=prof.min_depth,
                max_depth=prof.max_depth,
                temp_range=f"{prof.min_temp:.2f}-{prof.max_temp:.2f}°C",
                sal_range=f"{prof.min_sal:.2f}-{prof.max_sal:.2f} PSU",
                summary_text=summary_text
            )
            summaries.append(summary)
        
        # Bulk insert summaries
        session.bulk_save_objects(summaries)
        session.commit()
        session.close()
        
        print(f"✅ Generated {len(summaries)} profile summaries")
    
    def _create_summary_text(self, profile) -> str:
        """Create natural language summary"""
        date_str = profile.timestamp.strftime("%B %d, %Y")
        
        region = classify_ocean_region(profile.latitude, profile.longitude) or "an unclassified ocean region"
        lat = f"{abs(profile.latitude):.2f}°{'N' if profile.latitude >= 0 else 'S'}"
        lon = f"{abs(profile.longitude):.2f}°{'E' if profile.longitude >= 0 else 'W'}"
        return (
            f"ARGO float {profile.float_id}, cycle {profile.cycle_number}, measured on {date_str} "
            f"at {lat}, {lon} in {region}. "
            f"Pressure from {profile.min_depth:.1f} to {profile.max_depth:.1f} dbar. "
            f"Temperature range: {profile.min_temp:.2f}°C to {profile.max_temp:.2f}°C "
            f"(mean {profile.avg_temp:.2f}°C). "
            f"Salinity range: {profile.min_sal:.2f} to {profile.max_sal:.2f} PSU "
            f"(mean {profile.avg_sal:.2f} PSU)."
        )

# Usage
if __name__ == "__main__":
    summarizer = ProfileSummarizer()
    summarizer.generate_summaries()
