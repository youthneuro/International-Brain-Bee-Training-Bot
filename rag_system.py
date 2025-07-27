import os
import json
import hashlib
from typing import List, Dict, Optional
from openai import AzureOpenAI
import pickle
from pathlib import Path

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "")
)

class RAGSystem:
    def __init__(self):
        self.embeddings_cache_file = "embeddings_cache.pkl"
        self.chunk_size = 1000
        self.overlap = 200
        self.load_embeddings()
    
    def load_embeddings(self):
        """Load existing embeddings from cache or create new ones."""
        if os.path.exists(self.embeddings_cache_file):
            with open(self.embeddings_cache_file, 'rb') as f:
                self.embeddings_cache = pickle.load(f)
        else:
            self.embeddings_cache = {}
            self.create_embeddings_for_all_files()
    
    def create_embeddings_for_all_files(self):
        """Create embeddings for all text files."""
        categories = [
            "Sensory system", "Motor system", "Neural communication (electrical and chemical)",
            "Neuroanatomy", "Higher cognition", "Neurology (Diseases of the Brain)"
        ]
        
        for category in categories:
            filename = f"{category}.txt"
            if os.path.exists(filename):
                print(f"Creating embeddings for {category}...")
                self.create_embeddings_for_file(category, filename)
        
        # Save embeddings to cache
        with open(self.embeddings_cache_file, 'wb') as f:
            pickle.dump(self.embeddings_cache, f)
    
    def create_embeddings_for_file(self, category: str, filename: str):
        """Create embeddings for a specific text file."""
        with open(filename, 'r', encoding="utf-8") as file:
            content = file.read()
        
        # Split content into chunks
        chunks = self.split_into_chunks(content)
        
        # Create embeddings for each chunk
        embeddings = []
        for i, chunk in enumerate(chunks):
            embedding = self.create_embedding(chunk)
            embeddings.append({
                'text': chunk,
                'embedding': embedding,
                'category': category,
                'chunk_id': i
            })
        
        self.embeddings_cache[category] = embeddings
        print(f"Created {len(embeddings)} embeddings for {category}")
    
    def split_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Find the last sentence boundary in the chunk
                last_period = chunk.rfind('.')
                last_exclamation = chunk.rfind('!')
                last_question = chunk.rfind('?')
                last_newline = chunk.rfind('\n')
                
                # Find the latest boundary
                boundary = max(last_period, last_exclamation, last_question, last_newline)
                
                if boundary > self.chunk_size * 0.7:  # If boundary is in the last 30% of chunk
                    chunk = chunk[:boundary + 1]
                    end = start + len(chunk)
            
            chunks.append(chunk.strip())
            start = end - self.overlap  # Overlap for context continuity
    
        return chunks
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for a text chunk."""
        try:
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error creating embedding: {e}")
            return []
    
    def semantic_search(self, query: str, category: str, top_k: int = 3) -> List[str]:
        """Find the most semantically relevant chunks for a query."""
        if category not in self.embeddings_cache:
            print(f"No embeddings found for category: {category}")
            return []
        
        # Create embedding for the query
        query_embedding = self.create_embedding(query)
        if not query_embedding:
            return []
        
        # Calculate cosine similarity with all chunks in the category
        similarities = []
        for chunk_data in self.embeddings_cache[category]:
            similarity = self.cosine_similarity(query_embedding, chunk_data['embedding'])
            similarities.append((similarity, chunk_data['text']))
        
        # Sort by similarity and return top_k results
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in similarities[:top_k]]
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def get_relevant_content_rag(self, category: str, question_type: str = "multiple choice") -> str:
        """Get the most relevant content for question generation using RAG."""
        # Create a query that describes what we want
        query = f"Generate a {question_type} question about {category} in neuroscience"
        
        # Get the most relevant chunks
        relevant_chunks = self.semantic_search(query, category, top_k=3)
        
        if not relevant_chunks:
            # Fallback to random selection if no embeddings available
            print(f"RAG failed for {category}, falling back to random selection")
            return self.fallback_random_selection(category)
        
        # Combine relevant chunks
        relevant_content = "\n\n".join(relevant_chunks)
        
        # Ensure we don't exceed token limits
        if len(relevant_content) > 8000:
            relevant_content = relevant_content[:8000]
        
        return relevant_content
    
    def fallback_random_selection(self, category: str) -> str:
        """Fallback to random selection if RAG fails."""
        import random
        
        filename = f"{category}.txt"
        if not os.path.exists(filename):
            return ""
        
        with open(filename, 'r', encoding="utf-8") as file:
            information = file.read()
        
        if len(information) <= 8000:
            return information
        
        # Random selection logic (from simple_fallback.py)
        sections = []
        section_size = 2000
        num_sections = 4
        
        total_sections = len(information) // section_size
        
        if total_sections <= num_sections:
            return information[:8000]
        
        selected_indices = random.sample(range(total_sections), num_sections)
        
        for idx in selected_indices:
            start = idx * section_size
            end = start + section_size
            section = information[start:end]
            sections.append(section)
        
        relevant_content = " ".join(sections)
        
        if len(relevant_content) > 8000:
            relevant_content = relevant_content[:8000]
        
        return relevant_content

# Global RAG system instance
rag_system = RAGSystem()

def get_brain_bee_question_rag(category: str) -> str:
    """Get relevant content using RAG instead of random selection."""
    return rag_system.get_relevant_content_rag(category, "multiple choice") 