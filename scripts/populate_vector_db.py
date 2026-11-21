#!/usr/bin/env python3
"""
Populate or refresh the vector database.
Use this if you add new data to the database.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database.db_setup import DatabaseSetup
from database.models import ProfileSummary
from vector_store.embeddings import EmbeddingGenerator
from vector_store.vector_db import FAISSVectorStore

def main():
    print("🔄 Refreshing vector database...")
    
    # Initialize components
    db_setup = DatabaseSetup()
    embedding_generator = EmbeddingGenerator()
    
    # Get summaries from database
    session = db_setup.get_session()
    summaries = session.query(ProfileSummary).all()
    session.close()
    
    if not summaries:
        print("❌ No summaries found in database")
        return
    
    print(f"📊 Processing {len(summaries)} summaries...")
    
    # Generate embeddings
    texts = [s.summary_text for s in summaries]
    embeddings = embedding_generator.generate_embeddings(texts)
    
    # Create metadata
    metadata = [
        {
            'id': s.id,
            'float_id': s.float_id,
            'cycle_number': s.cycle_number,
            'timestamp': s.timestamp.isoformat(),
            'summary_text': s.summary_text,
            'latitude': s.latitude,
            'longitude': s.longitude
        }
        for s in summaries
    ]
    
    # Create and save vector store
    vector_store = FAISSVectorStore(dimension=embeddings.shape[1])
    vector_store.create_index()
    vector_store.add_vectors(embeddings, metadata)
    vector_store.save()
    
    print("✅ Vector database updated successfully!")

if __name__ == "__main__":
    main()
