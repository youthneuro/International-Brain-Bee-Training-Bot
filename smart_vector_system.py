import re
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Optional
import pickle
import os
import glob

class SmartVectorRetrievalSystem:
    def __init__(self, openai_client, model_name='all-MiniLM-L6-v2'):
        """
        Initialize the smart vector retrieval system with OpenAI integration.
        """
        self.model = SentenceTransformer(model_name)
        self.openai_client = openai_client
        self.chunks = []
        self.embeddings = []
        self.cache_file = 'embeddings_cache.pkl'
        
    def create_chunks(self, text: str, max_chunk_size: int = 1000) -> List[Dict]:
        """
        Create semantic chunks from text.
        """
        # Split by paragraphs first
        paragraphs = re.split(r'\n\n+', text)
        chunks = []
        
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if len(paragraph) < 50:  # Skip very short paragraphs
                continue
                
            # If paragraph is too long, split by sentences
            if len(paragraph) > max_chunk_size:
                sentences = re.split(r'[.!?]+', paragraph)
                current_chunk = ""
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(current_chunk) + len(sentence) < max_chunk_size:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            chunks.append({
                                'id': f"{i}_chunk",
                                'content': current_chunk.strip(),
                                'length': len(current_chunk)
                            })
                        current_chunk = sentence + ". "
                
                if current_chunk:
                    chunks.append({
                        'id': f"{i}_chunk",
                        'content': current_chunk.strip(),
                        'length': len(current_chunk)
                    })
            else:
                chunks.append({
                    'id': f"{i}",
                    'content': paragraph,
                    'length': len(paragraph)
                })
        
        return chunks
    
    def generate_smart_queries(self, category: str) -> List[str]:
        """
        Use OpenAI to generate intelligent queries for the category.
        """
        prompt = f"""You are a neuroscience expert. For the category "{category}", generate 3-5 search queries that would help find the most relevant content in a neuroscience textbook.

Focus on:
- Key concepts and terminology specific to {category}
- Anatomical structures related to {category}
- Functional aspects of {category}
- Clinical or research applications

Return only the queries, one per line, no explanations.

Examples for "Sensory system":
vision receptors
auditory processing
somatosensory pathways
sensory cortex function
perception mechanisms"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a neuroscience expert helping to find relevant content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            queries = response.choices[0].message.content.strip().split('\n')
            # Clean up queries and add the original category
            clean_queries = [category] + [q.strip() for q in queries if q.strip()]
            return clean_queries
            
        except Exception as e:
            print(f"⚠️  Failed to generate smart queries: {e}")
            # Fallback to just the category name
            return [category]
    
    def create_embeddings(self, text: str, force_recompute: bool = False):
        """
        Create vector embeddings for text chunks.
        """
        # Check if we have pre-computed embeddings
        if not force_recompute:
            # Try to load from pre-computed cache
            cache_file = self._get_cache_file_for_text(text)
            if cache_file and os.path.exists(cache_file):
                try:
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                        self.chunks = cached_data['chunks']
                        self.embeddings = cached_data['embeddings']
                        print("✅ Loaded pre-computed embeddings")
                        return
                except Exception as e:
                    print(f"⚠️  Failed to load pre-computed cache: {e}")
            
            # Fallback to old cache method
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                        self.chunks = cached_data['chunks']
                        self.embeddings = cached_data['embeddings']
                        print("✅ Loaded cached embeddings")
                        return
                except Exception as e:
                    print(f"⚠️  Failed to load cache: {e}")
        
        # Create new chunks and embeddings (fallback)
        print("🔄 Creating new embeddings...")
        self.chunks = self.create_chunks(text)
        
        if not self.chunks:
            print("❌ No chunks created from text")
            return
        
        # Extract text content for embedding
        chunk_texts = [chunk['content'] for chunk in self.chunks]
        
        # Create embeddings
        self.embeddings = self.model.encode(chunk_texts)
        
        # Cache the embeddings
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump({
                    'chunks': self.chunks,
                    'embeddings': self.embeddings
                }, f)
            print("✅ Cached embeddings for future use")
        except Exception as e:
            print(f"⚠️  Failed to cache embeddings: {e}")
    
    def _get_cache_file_for_text(self, text: str) -> Optional[str]:
        """
        Try to find the appropriate pre-computed cache file for the text.
        """
        # This is a simple heuristic - in practice, you'd want to match by content
        # For now, we'll assume the text comes from a file and try to match
        cache_dir = 'embeddings_cache'
        if not os.path.exists(cache_dir):
            return None
        
        # Look for cache files
        cache_files = glob.glob(os.path.join(cache_dir, "*_embeddings.pkl"))
        
        # For now, return the first one we find
        # In a more sophisticated system, you'd match by content hash or filename
        return cache_files[0] if cache_files else None
    
    def find_most_similar(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Find most similar chunks to the query.
        """
        if not self.embeddings or not self.chunks:
            print("❌ No embeddings available. Call create_embeddings() first.")
            return []
        
        # Encode the query
        query_embedding = self.model.encode([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # Get top k most similar chunks
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            content = self.chunks[idx]['content']
            score = similarities[idx]
            results.append((content, score))
        
        return results
    
    def get_relevant_content(self, category: str, max_length: int = 8000) -> str:
        """
        Get relevant content using AI-generated queries.
        """
        # Generate smart queries using OpenAI
        queries = self.generate_smart_queries(category)
        print(f"🔍 Generated queries for '{category}': {queries}")
        
        all_results = []
        
        # Get results for each AI-generated query
        for query in queries:
            results = self.find_most_similar(query, top_k=2)
            all_results.extend(results)
        
        # Remove duplicates and sort by similarity
        unique_results = {}
        for content, score in all_results:
            if content not in unique_results or score > unique_results[content]:
                unique_results[content] = score
        
        # Sort by similarity score
        sorted_results = sorted(unique_results.items(), key=lambda x: x[1], reverse=True)
        
        # Combine content within length limit
        combined_content = ""
        for content, score in sorted_results:
            if len(combined_content) + len(content) < max_length:
                combined_content += content + "\n\n"
            else:
                break
        
        return combined_content.strip()

# Global instance for reuse
smart_vector_system = None

def get_smart_vector_system(openai_client) -> SmartVectorRetrievalSystem:
    """
    Get or create the global smart vector retrieval system.
    """
    global smart_vector_system
    if smart_vector_system is None:
        smart_vector_system = SmartVectorRetrievalSystem(openai_client)
    return smart_vector_system

def get_brain_bee_question_with_smart_vectors(category: str, openai_client) -> str:
    """
    Generate Brain Bee question using AI-generated queries for content selection.
    """
    filename = category + ".txt"
    
    # Load text
    with open(filename, 'r', encoding="utf-8") as file:
        information = file.read()
    
    # Get smart vector system
    vs = get_smart_vector_system(openai_client)
    
    # Create embeddings (will use cache if available)
    vs.create_embeddings(information)
    
    # Get relevant content using AI-generated queries
    relevant_content = vs.get_relevant_content(category)
    
    return relevant_content 