"""
Run prediction → pick #1 coin → market buy 100% of cash balance on Alpaca
Runs at 23:55 UTC daily
"""
import os
import sys
import json
from alpaca.trade.client import TradeClient
from alpaca.trade.requests import MarketOrderRequest
from alpaca.trade.enums import OrderSide, TimeInForce
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.utils import COINS, get_db_connection, get_utc_now, format_date, get_logger

# Import the scorer dynamically
import importlib.util
spec = importlib.util.spec_from_file_location("current_scorer", os.path.join(os.path.dirname(os.path.dirname(__file__)), "current_scorer.py"))
current_scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(current_scorer)

if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    load_dotenv()
logger = get_logger('predict_and_trade')

def load_data():
    """Load price/volume data and sentiment data"""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Load price data
    data_file = os.path.join(base_dir, 'data_cache.json')
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Data file not found: {data_file}. Run 01_fetch_data.py first.")
    
    with open(data_file, 'r') as f:
        price_data = json.load(f)
    
    # Load sentiment data
    sentiment_file = os.path.join(base_dir, 'sentiment_cache.json')
    if not os.path.exists(sentiment_file):
        raise FileNotFoundError(f"Sentiment file not found: {sentiment_file}. Run 02_sentiment.py first.")
    
    with open(sentiment_file, 'r') as f:
        sentiment_data = json.load(f)
    
    return price_data, sentiment_data

def predict_best_coin(price_data, sentiment_data):
    """Use current_scorer to predict the best coin"""
    scores = {}
    
    for coin in COINS:
        if coin not in price_data:
            logger.warning(f"No price data for {coin}")
            continue
        
        if coin not in sentiment_data.get('sentiment', {}):
            logger.warning(f"No sentiment data for {coin}")
            continue
        
        coin_price = price_data[coin]
        coin_sentiment = sentiment_data['sentiment'][coin]
        
        # Score the coin using the current scorer
        score = current_scorer.score_coin(
            return_24h=coin_price.get('return_24h', 0),
            return_6h=coin_price.get('return_6h', 0),
            volume_ratio=coin_price.get('volume_ratio', 1.0),
            news_sentiment=coin_sentiment
        )
        
        scores[coin] = score
    
    if not scores:
        raise ValueError("No coins could be scored")
    
    # Find the coin with highest score
    best_coin = max(scores.items(), key=lambda x: x[1])
    return best_coin[0], best_coin[1], scores

def execute_trade(coin, client):
    """Execute market buy order for 100% of cash balance"""
    try:
        # Get account info
        account = client.get_account()
        cash = float(account.cash)
        
        if cash < 1:
            logger.warning(f"Insufficient cash: ${cash:.2f}")
            return None
        
        # Get current position
        positions = client.get_all_positions()
        current_position = None
        for pos in positions:
            if pos.symbol == coin:
                current_position = pos
                break
        
        # If we already have a position in this coin, don't trade
        if current_position:
            logger.info(f"Already have position in {coin}, skipping trade")
            return None
        
        # Close any other positions first
        for pos in positions:
            if pos.symbol != coin:
                logger.info(f"Closing position in {pos.symbol}")
                client.close_position(pos.symbol)
        
        # Place market buy order for 100% of cash
        # Note: Alpaca crypto uses notional (USD) orders
        order_request = MarketOrderRequest(
            symbol=coin,
            notional=cash,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )
        
        order = client.submit_order(order_request)
        logger.info(f"Order submitted: {order.id} - Buy ${cash:.2f} of {coin}")
        
        return order
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        return None

def record_prediction(coin, score, all_scores):
    """Record the prediction in database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = format_date(get_utc_now())
    
    # Check if prediction already exists
    cursor.execute("SELECT id FROM trades WHERE date = ?", (today,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing record
        cursor.execute("""
            UPDATE trades 
            SET chosen_coin = ?, chosen_score = ?
            WHERE date = ?
        """, (coin, score, today))
    else:
        # Insert new record
        cursor.execute("""
            INSERT INTO trades (date, chosen_coin, chosen_score)
            VALUES (?, ?, ?)
        """, (today, coin, score))
    
    conn.commit()
    conn.close()
    
    logger.info(f"Prediction recorded: {coin} with score {score:.4f}")

def main():
    """Main function"""
    logger.info(f"Running prediction and trade at {get_utc_now()}")
    
    # Load data
    price_data, sentiment_data = load_data()
    
    # Predict best coin
    best_coin, best_score, all_scores = predict_best_coin(price_data, sentiment_data)
    
    logger.info(f"Prediction Results:")
    logger.info(f"Best coin: {best_coin} (score: {best_score:.4f})")
    logger.info(f"All scores:")
    for coin, score in sorted(all_scores.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {coin}: {score:.4f}")
    
    # Record prediction
    record_prediction(best_coin, best_score, all_scores)
    
    # Execute trade
    try:
        client = TradeClient(
            api_key=os.getenv('ALPACA_KEY_ID'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        )
        
        order = execute_trade(best_coin, client)
        if order:
            logger.info(f"Trade executed successfully!")
        else:
            logger.info("Trade not executed (may already have position or insufficient funds)")
    except Exception as e:
        logger.error(f"Error connecting to Alpaca: {e}")
        logger.error("Make sure ALPACA_KEY_ID and ALPACA_SECRET_KEY are set correctly")

if __name__ == '__main__':
    main()

