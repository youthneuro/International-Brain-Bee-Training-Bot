#!/usr/bin/env python3
"""
Quick test script to verify the fixes work correctly.
"""

import os
from dotenv import load_dotenv
import json
import uuid

# Load environment variables
load_dotenv()

def test_azure_openai():
    """Test Azure OpenAI with the new API version."""
    print("🔍 Testing Azure OpenAI...")
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "")
        )
        
        # Test basic completion
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say 'Hello World'"}],
            max_tokens=10
        )
        
        if response.choices[0].message.content:
            print("✅ Azure OpenAI working!")
            return True
        else:
            print("❌ No response from Azure OpenAI")
            return False
            
    except Exception as e:
        print(f"❌ Azure OpenAI error: {e}")
        return False

def test_supabase_storage():
    """Test Supabase Storage with duplicate handling."""
    print("🔍 Testing Supabase Storage...")
    
    try:
        from supabase import create_client, Client
        
        SUPABASE_URL = os.getenv("SUPABASE_URL", "")
        SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY", "")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("❌ Supabase credentials not found!")
            return False
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test file upload
        test_data = {"test": "data", "timestamp": "2024-01-15T10:30:00Z"}
        test_filename = f"test/{uuid.uuid4()}.json"
        
        # First upload
        supabase.storage.from_("brain-bee-data").upload(
            path=test_filename,
            file=json.dumps(test_data).encode('utf-8'),
            file_options={"content-type": "application/json"}
        )
        print("✅ First upload successful")
        
        # Try to upload again (should replace)
        try:
            supabase.storage.from_("brain-bee-data").upload(
                path=test_filename,
                file=json.dumps(test_data).encode('utf-8'),
                file_options={"content-type": "application/json"}
            )
        except Exception as e:
            if "already exists" in str(e).lower():
                # Remove and re-upload
                try:
                    supabase.storage.from_("brain-bee-data").remove([test_filename])
                except:
                    pass
                supabase.storage.from_("brain-bee-data").upload(
                    path=test_filename,
                    file=json.dumps(test_data).encode('utf-8'),
                    file_options={"content-type": "application/json"}
                )
                print("✅ Duplicate handling working!")
            else:
                raise e
        
        # Clean up test file
        try:
            supabase.storage.from_("brain-bee-data").remove([test_filename])
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase Storage error: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Testing Fixes...")
    print("=" * 40)
    
    azure_ok = test_azure_openai()
    supabase_ok = test_supabase_storage()
    
    print("\n📊 Results:")
    print(f"Azure OpenAI: {'✅' if azure_ok else '❌'}")
    print(f"Supabase Storage: {'✅' if supabase_ok else '❌'}")
    
    if azure_ok and supabase_ok:
        print("\n🎉 All fixes working!")
        print("💡 You can now run: python app.py")
    else:
        print("\n⚠️  Some issues remain. Check the errors above.")

if __name__ == "__main__":
    main() 