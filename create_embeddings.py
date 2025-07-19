#!/usr/bin/env python3
"""
Pre-compute embeddings for all neuroscience text files.
Run this once to create cached embeddings for faster question generation.
"""

import os
import pickle
import re
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import glob

class EmbeddingPrecomputer:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """
        Initialize the embedding precomputer.
        """
        print(f"🔄 Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.cache_dir = 'embeddings_cache'
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
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
    
    def process_file(self, filename: str) -> Dict:
        """
        Process a single text file and create embeddings.
        """
        print(f"📖 Processing: {filename}")
        
        # Read the file
        with open(filename, 'r', encoding="utf-8") as file:
            text = file.read()
        
        # Create chunks
        chunks = self.create_chunks(text)
        print(f"   Created {len(chunks)} chunks")
        
        if not chunks:
            print(f"   ⚠️  No chunks created for {filename}")
            return {}
        
        # Extract text content for embedding
        chunk_texts = [chunk['content'] for chunk in chunks]
        
        # Create embeddings
        print(f"   🔄 Creating embeddings...")
        embeddings = self.model.encode(chunk_texts)
        
        # Save to cache
        cache_data = {
            'chunks': chunks,
            'embeddings': embeddings,
            'filename': filename,
            'chunk_count': len(chunks)
        }
        
        # Create cache filename
        base_name = os.path.splitext(os.path.basename(filename))[0]
        cache_file = os.path.join(self.cache_dir, f"{base_name}_embeddings.pkl")
        
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        
        print(f"   ✅ Saved embeddings to: {cache_file}")
        return cache_data
    
    def process_all_files(self):
        """
        Process all neuroscience text files.
        """
        # Find all .txt files
        txt_files = glob.glob("*.txt")
        
        # Filter for neuroscience files (exclude other .txt files)
        neuro_files = [f for f in txt_files if any(keyword in f.lower() for keyword in [
            'sensory', 'motor', 'neuro', 'cognition', 'development', 'cellular', 'neural'
        ])]
        
        print(f"🎯 Found {len(neuro_files)} neuroscience files to process:")
        for file in neuro_files:
            print(f"   - {file}")
        
        print("\n🚀 Starting embedding creation...")
        
        total_chunks = 0
        for filename in neuro_files:
            try:
                result = self.process_file(filename)
                if result:
                    total_chunks += result['chunk_count']
                print()  # Empty line for readability
            except Exception as e:
                print(f"   ❌ Error processing {filename}: {e}")
        
        print(f"✅ Completed! Created embeddings for {total_chunks} total chunks")
        print(f"📁 Cache files saved in: {self.cache_dir}/")
        print("\n🎉 Your app will now start much faster!")

def main():
    """
    Main function to run the embedding pre-computation.
    """
    print("🧠 Brain Bee Training Bot - Embedding Pre-computation")
    print("=" * 50)
    
    # Check if cache directory already exists
    if os.path.exists('embeddings_cache'):
        print("⚠️  Cache directory already exists.")
        response = input("Do you want to recreate all embeddings? (y/N): ")
        if response.lower() != 'y':
            print("Skipping pre-computation.")
            return
    
    # Create precomputer and process files
    precomputer = EmbeddingPrecomputer()
    precomputer.process_all_files()

if __name__ == "__main__":
    main() 