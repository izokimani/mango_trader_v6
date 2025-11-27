#!/usr/bin/env python3
"""
Comprehensive verification script to ensure the bot is perfect and ready to run
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('secrets.env')

def check_imports():
    """Check if all required modules can be imported"""
    print("Checking imports...")
    issues = []
    
    try:
        from polygon import RESTClient
        print("  ✓ polygon-api-client")
    except ImportError as e:
        issues.append(f"polygon-api-client: {e}")
        print(f"  ✗ polygon-api-client: {e}")
    
    try:
        from alpaca.trade.client import TradeClient
        print("  ✓ alpaca-trade-api")
    except ImportError as e:
        issues.append(f"alpaca-trade-api: {e}")
        print(f"  ✗ alpaca-trade-api: {e}")
    
    try:
        from openai import OpenAI
        print("  ✓ openai")
    except ImportError as e:
        issues.append(f"openai: {e}")
        print(f"  ✗ openai: {e}")
    
    try:
        import pandas as pd
        print("  ✓ pandas")
    except ImportError as e:
        issues.append(f"pandas: {e}")
        print(f"  ✗ pandas: {e}")
    
    try:
        import numpy as np
        print("  ✓ numpy")
    except ImportError as e:
        issues.append(f"numpy: {e}")
        print(f"  ✗ numpy: {e}")
    
    try:
        from scipy.stats import spearmanr
        print("  ✓ scipy")
    except ImportError as e:
        issues.append(f"scipy: {e}")
        print(f"  ✗ scipy: {e}")
    
    return issues

def check_api_keys():
    """Check if all API keys are set"""
    print("\nChecking API keys...")
    keys = {
        'ALPACA_KEY_ID': os.getenv('ALPACA_KEY_ID'),
        'ALPACA_SECRET_KEY': os.getenv('ALPACA_SECRET_KEY'),
        'POLYGON_KEY': os.getenv('POLYGON_KEY'),
        'PERPLEXITY_KEY': os.getenv('PERPLEXITY_KEY'),
    }
    
    all_set = True
    for key_name, value in keys.items():
        if not value or value.startswith('your_') or value.endswith('_here'):
            print(f"  ✗ {key_name}: NOT SET")
            all_set = False
        else:
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"  ✓ {key_name}: SET ({masked})")
    
    return all_set

def check_files():
    """Check if all required files exist"""
    print("\nChecking files...")
    required_files = [
        'current_scorer.py',
        'run.sh',
        'requirements.txt',
        'src/utils.py',
        'src/01_fetch_data.py',
        'src/02_sentiment.py',
        'src/03_predict_and_trade.py',
        'src/04_record_results.py',
        'src/05_self_improve.py',
        'src/06_sell_position.py',
        'src/07_self_analyze.py',
        'backtest.py',
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file}: MISSING")
            missing.append(file)
    
    return len(missing) == 0

def check_database():
    """Check if database can be initialized"""
    print("\nChecking database...")
    try:
        sys.path.append(os.path.dirname(__file__))
        from src.utils import init_database, get_db_connection
        
        init_database()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if 'trades' in tables and 'model_history' in tables:
            print("  ✓ Database initialized correctly")
            print(f"  ✓ Tables: {', '.join(tables)}")
            return True
        else:
            print(f"  ✗ Missing tables. Found: {tables}")
            return False
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        return False

def check_scorer():
    """Check if scorer can be loaded"""
    print("\nChecking scorer...")
    try:
        import importlib.util
        scorer_file = os.path.join(os.path.dirname(__file__), 'current_scorer.py')
        spec = importlib.util.spec_from_file_location("current_scorer", scorer_file)
        scorer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scorer_module)
        
        if hasattr(scorer_module, 'score_coin'):
            print("  ✓ scorer.score_coin function found")
            return True
        else:
            print("  ✗ score_coin function not found")
            return False
    except Exception as e:
        print(f"  ✗ Error loading scorer: {e}")
        return False

def check_logging():
    """Check if logging system works"""
    print("\nChecking logging...")
    try:
        sys.path.append(os.path.dirname(__file__))
        from src.utils import get_logger
        
        logger = get_logger('test')
        logger.info("Test log message")
        
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        if os.path.exists(log_dir):
            print("  ✓ Logging system works")
            print(f"  ✓ Log directory exists: {log_dir}")
            return True
        else:
            print("  ✗ Log directory not created")
            return False
    except Exception as e:
        print(f"  ✗ Logging error: {e}")
        return False

def main():
    print("="*60)
    print("BOT SETUP VERIFICATION")
    print("="*60)
    
    all_good = True
    
    # Check imports
    import_issues = check_imports()
    if import_issues:
        print(f"\n⚠ {len(import_issues)} import issues found. Run: pip install -r requirements.txt")
        all_good = False
    
    # Check API keys
    keys_ok = check_api_keys()
    if not keys_ok:
        print("\n⚠ Some API keys are missing. Edit secrets.env")
        all_good = False
    
    # Check files
    files_ok = check_files()
    if not files_ok:
        all_good = False
    
    # Check database
    db_ok = check_database()
    if not db_ok:
        all_good = False
    
    # Check scorer
    scorer_ok = check_scorer()
    if not scorer_ok:
        all_good = False
    
    # Check logging
    logging_ok = check_logging()
    if not logging_ok:
        all_good = False
    
    print("\n" + "="*60)
    if all_good and keys_ok:
        print("✓ BOT IS PERFECT AND READY TO RUN!")
        print("\nNext steps:")
        print("  1. Test data fetch: ./run.sh fetch_data")
        print("  2. Test sentiment: ./run.sh sentiment")
        print("  3. Set up cron jobs (see README.md)")
    else:
        print("⚠ SOME ISSUES FOUND - See above for details")
    print("="*60)

if __name__ == '__main__':
    main()

