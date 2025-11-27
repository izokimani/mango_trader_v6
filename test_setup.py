#!/usr/bin/env python3
"""
Test script to verify API keys and setup
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('secrets.env')

def check_key(key_name, value):
    """Check if a key is set"""
    if not value or value.startswith('your_') or value.endswith('_here'):
        return False, "NOT SET (placeholder)"
    return True, "SET ✓"

def main():
    print("="*60)
    print("API KEY VERIFICATION")
    print("="*60)
    
    keys = {
        'ALPACA_KEY_ID': os.getenv('ALPACA_KEY_ID'),
        'ALPACA_SECRET_KEY': os.getenv('ALPACA_SECRET_KEY'),
        'POLYGON_KEY': os.getenv('POLYGON_KEY'),
        'PERPLEXITY_KEY': os.getenv('PERPLEXITY_KEY'),
    }
    
    all_set = True
    for key_name, value in keys.items():
        is_set, status = check_key(key_name, value)
        if is_set:
            # Show first/last few chars for verification
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"{key_name:25} {status:20} ({masked})")
        else:
            print(f"{key_name:25} {status:20}")
            all_set = False
    
    print("="*60)
    
    # Check ALPACA_BASE_URL
    base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    print(f"ALPACA_BASE_URL: {base_url}")
    
    print("="*60)
    
    if all_set:
        print("✓ All API keys are configured!")
        print("\nYou can now run the bot:")
        print("  ./run.sh fetch_data")
        print("  ./run.sh sentiment")
        print("  ./run.sh predict_and_trade")
    else:
        print("⚠ Some API keys are missing or still have placeholder values")
        print("Please edit secrets.env and add your actual API keys")
    
    print("="*60)

if __name__ == '__main__':
    main()

