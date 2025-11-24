"""
Seed sample workflow recipes into database
Run once to populate initial recipes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_setup import DatabaseSetup
from database.models import WorkflowRecipe
import json


def seed_recipes():
    """Seed sample recipes"""
    
    db_setup = DatabaseSetup()
    session = db_setup.get_session()
    
    recipes = [
        {
            'name': '🌡️ Study Warm Water & Thermocline',
            'description': 'Analyze temperature profiles and calculate thermocline depth',
            'category': 'temperature',
            'difficulty': 'beginner',
            'steps': json.dumps([
                {'step': 1, 'action': 'Select region'},
                {'step': 2, 'action': 'Calculate thermocline'},
                {'step': 3, 'action': 'View results'}
            ]),
            'expected_result': 'Temperature profile with thermocline depth marked',
            'estimated_time': '2 minutes',
            'icon': '🌡️',
            'is_featured': 1
        },
        {
            'name': '⚖️ Compare Two Regions',
            'description': 'Side-by-side comparison of parameters between regions',
            'category': 'comparison',
            'difficulty': 'beginner',
            'steps': json.dumps([
                {'step': 1, 'action': 'Choose region 1'},
                {'step': 2, 'action': 'Choose region 2'},
                {'step': 3, 'action': 'Select parameter'},
                {'step': 4, 'action': 'Run comparison'}
            ]),
            'expected_result': 'Comparison table and charts',
            'estimated_time': '3 minutes',
            'icon': '⚖️',
            'is_featured': 1
        },
        {
            'name': '📍 Find Nearest Floats',
            'description': 'Locate ARGO floats near a specific location',
            'category': 'spatial',
            'difficulty': 'beginner',
            'steps': json.dumps([
                {'step': 1, 'action': 'Enter coordinates'},
                {'step': 2, 'action': 'Set search radius'},
                {'step': 3, 'action': 'Find floats'}
            ]),
            'expected_result': 'Map with nearest floats and distances',
            'estimated_time': '1 minute',
            'icon': '📍',
            'is_featured': 1
        }
    ]
    
    try:
        for recipe_data in recipes:
            recipe = WorkflowRecipe(**recipe_data)
            session.add(recipe)
        
        session.commit()
        print(f"✅ Seeded {len(recipes)} workflow recipes")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding recipes: {e}")
    
    finally:
        session.close()


if __name__ == "__main__":
    seed_recipes()