"""
Utility functions shared across modules
"""
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables (from secrets.env if exists, otherwise use system env vars)
if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    # On Render or other cloud platforms, env vars are already set
    load_dotenv()

def setup_logger(name, log_file=None):
    """Setup logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S UTC'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler
    if log_file is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        today = datetime.utcnow().strftime('%Y-%m-%d')
        log_file = os.path.join(log_dir, f'{today}.log')
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(module_name):
    """Get logger for a module"""
    return setup_logger(module_name)

# Coin list
COINS = [
    'BTCUSD', 'ETHUSD', 'SOLUSD', 'ADAUSD', 'DOGEUSD', 'AVAXUSD', 
    'LINKUSD', 'MATICUSD', 'DOTUSD', 'LTCUSD', 'BCHUSD', 'XLMUSD', 
    'ALGOUSD', 'UNIUSD', 'AAVEUSD', 'MKRUSD'
]

def get_db_connection():
    """Get SQLite database connection"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'trades.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the trades database with schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create trades table with 120+ columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            chosen_coin TEXT,
            chosen_score REAL,
            actual_24h_return_of_chosen REAL,
            rank_of_chosen INTEGER,
            -- Returns for all coins
            BTCUSD_return_1h REAL, BTCUSD_return_6h REAL, BTCUSD_return_24h REAL,
            ETHUSD_return_1h REAL, ETHUSD_return_6h REAL, ETHUSD_return_24h REAL,
            SOLUSD_return_1h REAL, SOLUSD_return_6h REAL, SOLUSD_return_24h REAL,
            ADAUSD_return_1h REAL, ADAUSD_return_6h REAL, ADAUSD_return_24h REAL,
            DOGEUSD_return_1h REAL, DOGEUSD_return_6h REAL, DOGEUSD_return_24h REAL,
            AVAXUSD_return_1h REAL, AVAXUSD_return_6h REAL, AVAXUSD_return_24h REAL,
            LINKUSD_return_1h REAL, LINKUSD_return_6h REAL, LINKUSD_return_24h REAL,
            MATICUSD_return_1h REAL, MATICUSD_return_6h REAL, MATICUSD_return_24h REAL,
            DOTUSD_return_1h REAL, DOTUSD_return_6h REAL, DOTUSD_return_24h REAL,
            LTCUSD_return_1h REAL, LTCUSD_return_6h REAL, LTCUSD_return_24h REAL,
            BCHUSD_return_1h REAL, BCHUSD_return_6h REAL, BCHUSD_return_24h REAL,
            XLMUSD_return_1h REAL, XLMUSD_return_6h REAL, XLMUSD_return_24h REAL,
            ALGOUSD_return_1h REAL, ALGOUSD_return_6h REAL, ALGOUSD_return_24h REAL,
            UNIUSD_return_1h REAL, UNIUSD_return_6h REAL, UNIUSD_return_24h REAL,
            AAVEUSD_return_1h REAL, AAVEUSD_return_6h REAL, AAVEUSD_return_24h REAL,
            MKRUSD_return_1h REAL, MKRUSD_return_6h REAL, MKRUSD_return_24h REAL,
            -- RSI for all coins
            BTCUSD_rsi_14 REAL, ETHUSD_rsi_14 REAL, SOLUSD_rsi_14 REAL,
            ADAUSD_rsi_14 REAL, DOGEUSD_rsi_14 REAL, AVAXUSD_rsi_14 REAL,
            LINKUSD_rsi_14 REAL, MATICUSD_rsi_14 REAL, DOTUSD_rsi_14 REAL,
            LTCUSD_rsi_14 REAL, BCHUSD_rsi_14 REAL, XLMUSD_rsi_14 REAL,
            ALGOUSD_rsi_14 REAL, UNIUSD_rsi_14 REAL, AAVEUSD_rsi_14 REAL,
            MKRUSD_rsi_14 REAL,
            -- Volume ratios for all coins
            BTCUSD_volume_ratio REAL, ETHUSD_volume_ratio REAL, SOLUSD_volume_ratio REAL,
            ADAUSD_volume_ratio REAL, DOGEUSD_volume_ratio REAL, AVAXUSD_volume_ratio REAL,
            LINKUSD_volume_ratio REAL, MATICUSD_volume_ratio REAL, DOTUSD_volume_ratio REAL,
            LTCUSD_volume_ratio REAL, BCHUSD_volume_ratio REAL, XLMUSD_volume_ratio REAL,
            ALGOUSD_volume_ratio REAL, UNIUSD_volume_ratio REAL, AAVEUSD_volume_ratio REAL,
            MKRUSD_volume_ratio REAL,
            -- News sentiment scores
            BTCUSD_news_sentiment REAL, ETHUSD_news_sentiment REAL, SOLUSD_news_sentiment REAL,
            ADAUSD_news_sentiment REAL, DOGEUSD_news_sentiment REAL, AVAXUSD_news_sentiment REAL,
            LINKUSD_news_sentiment REAL, MATICUSD_news_sentiment REAL, DOTUSD_news_sentiment REAL,
            LTCUSD_news_sentiment REAL, BCHUSD_news_sentiment REAL, XLMUSD_news_sentiment REAL,
            ALGOUSD_news_sentiment REAL, UNIUSD_news_sentiment REAL, AAVEUSD_news_sentiment REAL,
            MKRUSD_news_sentiment REAL,
            -- Raw news data
            news_headlines TEXT,
            perplexity_summary TEXT,
            model_version INTEGER DEFAULT 1
        )
    ''')
    
    # Create model_history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            version INTEGER,
            scorer_code TEXT,
            spearman_correlation REAL,
            avg_daily_return REAL,
            improvement_type TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_utc_now():
    """Get current UTC datetime"""
    return datetime.utcnow()

def format_date(dt):
    """Format datetime as YYYY-MM-DD"""
    return dt.strftime('%Y-%m-%d')

