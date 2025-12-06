#!/usr/bin/env python3
"""Quick test: Check if Anthropic API key is loaded and working"""

import os
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ dotenv loaded")
except ImportError:
    # Manual .env loading
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
        print("✅ .env loaded manually")

# Check API key
api_key = os.getenv('ANTHROPIC_API_KEY')
print(f"\nANTHROPIC_API_KEY status: {'SET (' + str(len(api_key)) + ' chars)' if api_key else 'NOT SET'}")

if not api_key:
    print("❌ API key not found in environment")
    exit(1)

# Try to initialize Anthropic client
try:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    print("✅ Anthropic client initialized successfully")

    # Try a minimal API call
    print("\nTesting API with minimal call...")
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=10,
        messages=[{"role": "user", "content": "Hi"}]
    )
    print(f"✅ API call successful! Response: {response.content[0].text}")

except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
