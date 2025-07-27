#!/usr/bin/env python3
"""
Initialize RAG system by creating embeddings for all text files.
Run this script once to set up the RAG system.
"""

import os
from dotenv import load_dotenv
from rag_system import RAGSystem

def main():
    """Initialize the RAG system."""
    print("🚀 Initializing RAG system for Brain Bee Training Bot...")
    
    # Load environment variables
    load_dotenv()
    
    # Check if Azure OpenAI credentials are available
    if not os.getenv("AZURE_OPENAI_API_KEY") or not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("❌ Error: Azure OpenAI credentials not found!")
        print("Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT in your .env file")
        return
    
    # Check if text files exist
    categories = [
        "Sensory system", "Motor system", "Neural communication (electrical and chemical)",
        "Neuroanatomy", "Higher cognition", "Neurology (Diseases of the Brain)"
    ]
    
    missing_files = []
    for category in categories:
        filename = f"{category}.txt"
        if not os.path.exists(filename):
            missing_files.append(filename)
    
    if missing_files:
        print(f"❌ Missing text files: {missing_files}")
        print("Please ensure all category text files are present in the current directory")
        return
    
    print("✅ All text files found")
    print("📚 Creating embeddings for all categories...")
    
    try:
        # Initialize RAG system (this will create embeddings)
        rag_system = RAGSystem()
        
        print("✅ RAG system initialized successfully!")
        print("📊 Embeddings created for all categories")
        print("🎯 Your Brain Bee bot now uses intelligent content retrieval!")
        
        # Show some stats
        total_chunks = 0
        for category, embeddings in rag_system.embeddings_cache.items():
            total_chunks += len(embeddings)
            print(f"   - {category}: {len(embeddings)} chunks")
        
        print(f"\n📈 Total chunks indexed: {total_chunks}")
        print("🚀 Ready to generate intelligent questions!")
        
    except Exception as e:
        print(f"❌ Error initializing RAG system: {e}")
        print("Please check your Azure OpenAI credentials and try again")

if __name__ == "__main__":
    main() 