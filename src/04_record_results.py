"""
After 24h sell → record actual 24h % return for every coin → calculate rank
Runs at 00:15 UTC daily (after selling position)
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.utils import COINS, get_db_connection, get_utc_now, format_date, get_logger, init_database

if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    load_dotenv()
logger = get_logger('record_results')


def fetch_actual_returns():
    """Fetch actual 24h returns for all coins"""
    from polygon.rest import RESTClient
    from datetime import datetime, timedelta
    
    client = RESTClient(os.getenv('POLYGON_KEY'))
    returns = {}
    
    now = datetime.utcnow()
    yesterday = now - timedelta(hours=24)
    
    for coin in COINS:
        try:
            polygon_symbol = f"X:{coin}"
            
            # Get price 24h ago (need to get actual hour data)
            # Get last 48 hours to ensure we have the data point we need
            aggs_24h = client.get_aggs(
                ticker=polygon_symbol,
                multiplier=1,
                timespan="hour",
                from_=int((yesterday - timedelta(hours=2)).timestamp() * 1000),
                to=int((yesterday + timedelta(hours=2)).timestamp() * 1000)
            )
            
            # Get current price (last few hours)
            aggs_now = client.get_aggs(
                ticker=polygon_symbol,
                multiplier=1,
                timespan="hour",
                from_=int((now - timedelta(hours=2)).timestamp() * 1000),
                to=int(now.timestamp() * 1000)
            )
            
            if aggs_24h and aggs_now:
                price_24h_ago = aggs_24h[-1].close if aggs_24h else None
                price_now = aggs_now[-1].close if aggs_now else None
                
                if price_24h_ago and price_now and price_24h_ago > 0:
                    return_pct = (price_now / price_24h_ago - 1) * 100
                    returns[coin] = return_pct
                else:
                    returns[coin] = 0.0
            else:
                returns[coin] = 0.0
        except Exception as e:
            logger.error(f"Error fetching return for {coin}: {e}")
            returns[coin] = 0.0
    
    return returns

def calculate_rank(chosen_coin, all_returns):
    """Calculate where chosen coin ranked (1-16)"""
    sorted_coins = sorted(all_returns.items(), key=lambda x: x[1], reverse=True)
    
    for rank, (coin, return_pct) in enumerate(sorted_coins, 1):
        if coin == chosen_coin:
            return rank, sorted_coins
    
    return 16, sorted_coins  # Worst case

def load_yesterday_data():
    """Load yesterday's prediction data"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Try to load from cache files (if they exist)
    data_file = os.path.join(base_dir, 'data_cache.json')
    sentiment_file = os.path.join(base_dir, 'sentiment_cache.json')
    
    price_data = {}
    sentiment_data = {}
    
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            price_data = json.load(f)
    
    if os.path.exists(sentiment_file):
        with open(sentiment_file, 'r') as f:
            sentiment_data = json.load(f)
    
    return price_data, sentiment_data

def record_results(chosen_coin, actual_return, rank, all_returns, price_data, sentiment_data):
    """Record all results in database"""
    init_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    yesterday = format_date(get_utc_now() - timedelta(days=1))
    
    # Build update query with all coin data
    update_fields = ['actual_24h_return_of_chosen = ?, rank_of_chosen = ?']
    values = [actual_return, rank]
    
    # Add returns for all coins
    for coin in COINS:
        return_val = all_returns.get(coin, 0.0)
        update_fields.append(f"{coin}_return_24h = ?")
        values.append(return_val)
        
        # Add 1h and 6h returns if available
        if coin in price_data:
            update_fields.append(f"{coin}_return_1h = ?")
            values.append(price_data[coin].get('return_1h', 0.0))
            update_fields.append(f"{coin}_return_6h = ?")
            values.append(price_data[coin].get('return_6h', 0.0))
            update_fields.append(f"{coin}_rsi_14 = ?")
            values.append(price_data[coin].get('rsi_14', 50.0))
            update_fields.append(f"{coin}_volume_ratio = ?")
            values.append(price_data[coin].get('volume_ratio', 1.0))
        else:
            update_fields.extend([f"{coin}_return_1h = ?", f"{coin}_return_6h = ?", 
                                 f"{coin}_rsi_14 = ?", f"{coin}_volume_ratio = ?"])
            values.extend([0.0, 0.0, 50.0, 1.0])
        
        # Add sentiment
        sentiment_val = sentiment_data.get('sentiment', {}).get(coin, 0.0)
        update_fields.append(f"{coin}_news_sentiment = ?")
        values.append(sentiment_val)
    
    # Add news headlines and summary
    headlines_text = ""
    summary_text = ""
    if chosen_coin in sentiment_data.get('headlines', {}):
        headlines = sentiment_data['headlines'][chosen_coin]
        headlines_text = "\n".join([h.get('title', '') for h in headlines[:5]])
    if chosen_coin in sentiment_data.get('summaries', {}):
        summary_text = sentiment_data['summaries'].get(chosen_coin, '')
    
    update_fields.append("news_headlines = ?")
    values.append(headlines_text)
    update_fields.append("perplexity_summary = ?")
    values.append(summary_text)
    
    values.append(yesterday)
    
    query = f"""
        UPDATE trades 
        SET {', '.join(update_fields)}
        WHERE date = ?
    """
    
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    
    logger.info(f"Results recorded for {yesterday}")

def main():
    """Main function"""
    logger.info(f"Recording results at {get_utc_now()}")
    
    # Initialize database first
    init_database()
    
    # Note: Position should have been sold at 23:59 by 06_sell_position.py
    # This script just records the results
    
    # Get yesterday's chosen coin
    conn = get_db_connection()
    cursor = conn.cursor()
    yesterday = format_date(get_utc_now() - timedelta(days=1))
    
    cursor.execute("SELECT chosen_coin FROM trades WHERE date = ?", (yesterday,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        logger.warning(f"No prediction found for {yesterday}")
        return
    
    chosen_coin = result['chosen_coin']
    logger.info(f"Yesterday's chosen coin: {chosen_coin}")
    
    # Fetch actual returns
    all_returns = fetch_actual_returns()
    
    # Calculate rank
    actual_return = all_returns.get(chosen_coin, 0.0)
    rank, sorted_coins = calculate_rank(chosen_coin, all_returns)
    
    logger.info(f"Actual Results:")
    logger.info(f"Chosen coin ({chosen_coin}): {actual_return:.2f}% (Rank: {rank}/16)")
    logger.info(f"Top 5 performers:")
    for i, (coin, ret) in enumerate(sorted_coins[:5], 1):
        logger.info(f"  {i}. {coin}: {ret:.2f}%")
    
    # Load yesterday's data
    price_data, sentiment_data = load_yesterday_data()
    
    # Record results
    record_results(chosen_coin, actual_return, rank, all_returns, price_data, sentiment_data)
    
    logger.info("Results recording complete")

if __name__ == '__main__':
    main()

