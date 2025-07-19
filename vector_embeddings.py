# Advanced: Vector Embeddings for Semantic Search
# This requires additional dependencies: pip install sentence-transformers

from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class VectorRetrievalSystem:
    def __init__(self):
        # Load a pre-trained model for neuroscience text
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Good for semantic similarity
        self.chunks = []
        self.embeddings = []
    
    def create_embeddings(self, text_chunks):
        """
        Create vector embeddings for text chunks.
        """
        self.chunks = text_chunks
        self.embeddings = self.model.encode(text_chunks)
    
    def find_most_similar(self, query, top_k=3):
        """
        Find most similar chunks to the query.
        """
        query_embedding = self.model.encode([query])
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # Get top k most similar chunks
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [self.chunks[i] for i in top_indices]

def get_brain_bee_question_with_vectors(category):
    """
    Question generation using vector embeddings for semantic search.
    """
    # This would require installing: pip install sentence-transformers scikit-learn
    
    # Load and chunk the text
    filename = category + ".txt"
    with open(filename, 'r', encoding="utf-8") as file:
        information = file.read()
    
    # Create chunks
    chunks = create_semantic_chunks(information)
    chunk_texts = [chunk['content'] for chunk in chunks]
    
    # Create vector retrieval system
    retrieval_system = VectorRetrievalSystem()
    retrieval_system.create_embeddings(chunk_texts)
    
    # Find most relevant chunks for the category
    relevant_chunks = retrieval_system.find_most_similar(category, top_k=3)
    
    # Combine relevant content
    relevant_content = "\n\n".join(relevant_chunks)
    
    # Use in prompt
    prompt = f"""Based on the following neuroscience information about {category}, create a Brain Bee question:

{relevant_content}

Generate a challenging question..."""
    
    return prompt 