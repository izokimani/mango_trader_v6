"""
Fetch last 72 hours of price/volume data for all 16 coins from Polygon
Runs at 23:50 UTC daily
"""
import os
import sys
from datetime import datetime, timedelta
from polygon.rest import RESTClient
from dotenv import load_dotenv
import pandas as pd
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.utils import COINS, get_db_connection, get_utc_now, format_date, get_logger

if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    load_dotenv()
logger = get_logger('fetch_data')

def fetch_polygon_data(coin, hours=72):
    """Fetch price and volume data for a coin"""
    client = RESTClient(os.getenv('POLYGON_KEY'))
    
    # Convert coin symbol (e.g., BTCUSD -> X:BTCUSD)
    polygon_symbol = f"X:{coin}"
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    try:
        # Get aggregates (bars)
        # Polygon API expects timestamps in milliseconds or date strings
        aggs = client.get_aggs(
            ticker=polygon_symbol,
            multiplier=1,
            timespan="hour",
            from_=int(start_time.timestamp() * 1000),  # Convert to milliseconds
            to=int(end_time.timestamp() * 1000)  # Convert to milliseconds
        )
        
        if not aggs:
            logger.warning(f"No data for {coin}")
            return None
        
        # Convert to DataFrame
        data = []
        for agg in aggs:
            data.append({
                'timestamp': datetime.fromtimestamp(agg.timestamp / 1000),
                'open': agg.open,
                'high': agg.high,
                'low': agg.low,
                'close': agg.close,
                'volume': agg.volume
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('timestamp')
        
        return df
    except Exception as e:
        logger.error(f"Error fetching data for {coin}: {e}")
        return None

def calculate_returns_and_indicators(df):
    """Calculate returns and technical indicators"""
    if df is None or len(df) < 24:
        return None
    
    # Calculate returns
    current_price = df['close'].iloc[-1]
    
    # Find prices at different time intervals
    now = df['timestamp'].iloc[-1]
    
    # 1 hour ago
    one_hour_ago = now - timedelta(hours=1)
    price_1h = df[df['timestamp'] <= one_hour_ago]['close'].iloc[-1] if len(df[df['timestamp'] <= one_hour_ago]) > 0 else current_price
    
    # 6 hours ago
    six_hours_ago = now - timedelta(hours=6)
    price_6h = df[df['timestamp'] <= six_hours_ago]['close'].iloc[-1] if len(df[df['timestamp'] <= six_hours_ago]) > 0 else current_price
    
    # 24 hours ago
    twenty_four_hours_ago = now - timedelta(hours=24)
    price_24h = df[df['timestamp'] <= twenty_four_hours_ago]['close'].iloc[-1] if len(df[df['timestamp'] <= twenty_four_hours_ago]) > 0 else current_price
    
    # Calculate returns
    return_1h = (current_price / price_1h - 1) * 100 if price_1h > 0 else 0
    return_6h = (current_price / price_6h - 1) * 100 if price_6h > 0 else 0
    return_24h = (current_price / price_24h - 1) * 100 if price_24h > 0 else 0
    
    # Calculate RSI (14 period)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi_14 = 100 - (100 / (1 + rs))
    rsi_14 = rsi_14.iloc[-1] if not pd.isna(rsi_14.iloc[-1]) else 50
    
    # Calculate volume ratio (current 24h volume vs previous 24h volume)
    recent_24h_volume = df[df['timestamp'] >= twenty_four_hours_ago]['volume'].sum()
    previous_24h_start = twenty_four_hours_ago - timedelta(hours=24)
    previous_24h_volume = df[(df['timestamp'] >= previous_24h_start) & (df['timestamp'] < twenty_four_hours_ago)]['volume'].sum()
    volume_ratio = recent_24h_volume / previous_24h_volume if previous_24h_volume > 0 else 1.0
    
    return {
        'return_1h': return_1h,
        'return_6h': return_6h,
        'return_24h': return_24h,
        'rsi_14': rsi_14,
        'volume_ratio': volume_ratio,
        'current_price': current_price
    }

def main():
    """Main function to fetch data for all coins"""
    logger.info(f"Fetching data at {get_utc_now()}")
    
    all_data = {}
    
    for coin in COINS:
        logger.info(f"Fetching {coin}...")
        df = fetch_polygon_data(coin, hours=72)
        if df is not None:
            indicators = calculate_returns_and_indicators(df)
            if indicators:
                all_data[coin] = indicators
                logger.info(f"{coin}: 24h return={indicators['return_24h']:.2f}%, volume_ratio={indicators['volume_ratio']:.2f}")
    
    # Save to JSON file for other modules to use
    output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data_cache.json')
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    logger.info(f"Data saved to {output_file}")
    logger.info(f"Fetched data for {len(all_data)} coins")

if __name__ == '__main__':
    main()

