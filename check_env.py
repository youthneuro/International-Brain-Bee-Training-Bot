import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=== Environment Variables Check ===")
print()

# Check each environment variable
env_vars = [
    "FLASK_SECRET_KEY",
    "AZURE_OPENAI_API_KEY", 
    "AZURE_OPENAI_ENDPOINT",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY"
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Show first 10 characters for security
        display_value = value[:10] + "..." if len(value) > 10 else value
        print(f"✅ {var}: {display_value}")
    else:
        print(f"❌ {var}: NOT SET")

print()
print("If you see ❌, those variables are missing from your .env file") 