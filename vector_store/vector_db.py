import os
import faiss
import numpy as np
import pickle
from typing import List, Tuple
from pathlib import Path

class FAISSVectorStore:
    """FAISS vector database for profile summaries"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = None
        self.metadata = []
        
        # Get vector store path, handle both relative and absolute
        store_path_str = os.getenv('VECTOR_STORE_PATH', './data/vector_store')
        self.store_path = Path(store_path_str)
        
        # If relative path and doesn't exist, try from project root
        if not self.store_path.is_absolute() and not self.store_path.exists():
            project_root = Path(__file__).parent.parent
            self.store_path = project_root / store_path_str.lstrip('./')
        
        self.store_path.mkdir(parents=True, exist_ok=True)
    
    def create_index(self):
        """Create new FAISS index"""
        # Using L2 distance for similarity
        self.index = faiss.IndexFlatL2(self.dimension)
        print(f"✅ Created FAISS index with dimension {self.dimension}")
    
    def add_vectors(self, embeddings: np.ndarray, metadata: List[dict]):
        """Add vectors to index"""
        if self.index is None:
            self.create_index()
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        self.index.add(embeddings.astype('float32'))
        self.metadata.extend(metadata)
        
        print(f"✅ Added {len(embeddings)} vectors to index")
        print(f"📊 Total vectors in index: {self.index.ntotal}")
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[float, dict]]:
        """Search for similar vectors"""
        if self.index is None or self.index.ntotal == 0:
            print("❌ Index is empty")
            return []
        
        # Normalize query
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(self.metadata):
                results.append((float(dist), self.metadata[idx]))
        
        return results
    
    def save(self):
        """Save index and metadata to disk"""
        faiss.write_index(self.index, str(self.store_path / "index.faiss"))
        with open(self.store_path / "metadata.pkl", 'wb') as f:
            pickle.dump(self.metadata, f)
        print(f"✅ Saved vector store to {self.store_path}")
    
    def load(self):
        """Load index and metadata from disk"""
        index_path = self.store_path / "index.faiss"
        metadata_path = self.store_path / "metadata.pkl"
        
        if not index_path.exists() or not metadata_path.exists():
            print(f"❌ Vector store not found at {self.store_path}")
            print(f"   Index exists: {index_path.exists()}")
            print(f"   Metadata exists: {metadata_path.exists()}")
            return False
        
        try:
            self.index = faiss.read_index(str(index_path))
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            
            print(f"✅ Loaded vector store with {self.index.ntotal} vectors")
            return True
        except Exception as e:
            print(f"❌ Error loading vector store: {e}")
            return False

# Usage
if __name__ == "__main__":
    store = FAISSVectorStore(dimension=384)
    store.create_index()
    
    # Test with dummy data
    test_embeddings = np.random.rand(10, 384).astype('float32')
    test_metadata = [{'id': i, 'text': f'Profile {i}'} for i in range(10)]
    
    store.add_vectors(test_embeddings, test_metadata)
    store.save()
