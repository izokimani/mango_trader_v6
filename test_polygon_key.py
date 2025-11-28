#!/usr/bin/env python3
"""Test script to verify Polygon API key"""
import os
from dotenv import load_dotenv
from polygon.rest import RESTClient

# Load environment variables
script_dir = os.path.dirname(__file__)
secrets_path = os.path.join(script_dir, 'secrets.env')
if os.path.exists(secrets_path):
    load_dotenv(secrets_path)
else:
    load_dotenv('secrets.env')

polygon_key = os.getenv('POLYGON_KEY', '').strip()

if not polygon_key:
    print("ERROR: POLYGON_KEY not found in environment variables!")
    exit(1)

print(f"API Key loaded: {len(polygon_key)} characters")
print(f"Key starts with: {polygon_key[:10]}...")

try:
    client = RESTClient(polygon_key)
    print("RESTClient created successfully")
    
    # Test with a simple API call
    print("\nTesting API call to get ticker details for BTCUSD...")
    result = client.get_ticker_details('X:BTCUSD')
    print(f"SUCCESS! API key is valid.")
    print(f"Ticker: {result.name if hasattr(result, 'name') else 'N/A'}")
    
except Exception as e:
    error_msg = str(e)
    print(f"\nERROR: API call failed: {error_msg}")
    
    if "Unknown API Key" in error_msg or "Invalid API Key" in error_msg or "401" in error_msg:
        print("\n" + "="*60)
        print("This appears to be an API key authentication error.")
        print("Possible causes:")
        print("1. The API key is invalid or expired")
        print("2. The API key doesn't have the required permissions")
        print("3. The API key format is incorrect")
        print("\nPlease verify your API key at: https://polygon.io/dashboard/api-keys")
        print("="*60)
    exit(1)

