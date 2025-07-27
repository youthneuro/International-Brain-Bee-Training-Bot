#!/usr/bin/env python3
"""
Script to check Azure OpenAI configuration and help debug endpoint issues.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_azure_config():
    """Check Azure OpenAI configuration."""
    print("🔍 Checking Azure OpenAI Configuration...")
    print("=" * 50)
    
    # Check environment variables
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    
    if not api_key:
        print("❌ AZURE_OPENAI_API_KEY not set")
        return False
    
    if not endpoint:
        print("❌ AZURE_OPENAI_ENDPOINT not set")
        return False
    
    print(f"✅ API Key: {api_key[:10]}...")
    print(f"✅ Endpoint: {endpoint}")
    
    # Check endpoint format
    if not endpoint.startswith("https://"):
        print("⚠️  Endpoint should start with https://")
    
    if not endpoint.endswith("/"):
        print("⚠️  Endpoint should end with /")
        endpoint = endpoint + "/"
    
    # Test different API versions
    api_versions = [
        "2024-05-01",
        "2024-02-15-preview", 
        "2024-01-01",
        "2023-12-01-preview"
    ]
    
    print("\n🔍 Testing API versions...")
    
    for version in api_versions:
        try:
            from openai import AzureOpenAI
            
            client = AzureOpenAI(
                api_key=api_key,
                api_version=version,
                azure_endpoint=endpoint
            )
            
            # Test basic completion
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            
            if response.choices[0].message.content:
                print(f"✅ API version {version} works!")
                return True
                
        except Exception as e:
            print(f"❌ API version {version} failed: {str(e)[:100]}...")
            continue
    
    print("\n❌ All API versions failed")
    return False

def check_model_availability():
    """Check what models are available."""
    print("\n🔍 Checking Model Availability...")
    print("=" * 50)
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-05-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "")
        )
        
        # Test different model names
        model_names = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4",
            "gpt-35-turbo",
            "gpt-35-turbo-16k"
        ]
        
        for model in model_names:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                print(f"✅ Model {model} available")
            except Exception as e:
                print(f"❌ Model {model} not available: {str(e)[:50]}...")
                
    except Exception as e:
        print(f"❌ Error checking models: {e}")

def main():
    """Main function."""
    print("🚀 Azure OpenAI Configuration Check")
    print("=" * 60)
    
    # Check configuration
    config_ok = check_azure_config()
    
    if config_ok:
        # Check models
        check_model_availability()
        
        print("\n💡 If you see model availability issues:")
        print("1. Check your Azure OpenAI resource in Azure Portal")
        print("2. Make sure the model is deployed to your resource")
        print("3. Verify your endpoint URL is correct")
        print("4. Check your API key permissions")
    else:
        print("\n🚨 Fix Azure OpenAI Configuration:")
        print("1. Go to Azure Portal → Azure OpenAI")
        print("2. Copy the endpoint URL (should end with /)")
        print("3. Copy the API key from Keys section")
        print("4. Add to your .env file:")
        print("   AZURE_OPENAI_API_KEY=your_key")
        print("   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")

if __name__ == "__main__":
    main() 