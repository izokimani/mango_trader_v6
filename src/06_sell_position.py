"""
Market sell 100% of position (exactly 24h after buying)
Runs at 23:59 UTC daily
"""
import os
import sys
from alpaca.trade.client import TradeClient
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.utils import get_utc_now, get_logger

if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    load_dotenv()
logger = get_logger('sell_position')

def sell_all_positions(client):
    """Sell 100% of all current positions"""
    try:
        positions = client.get_all_positions()
        if not positions:
            logger.info("No positions to sell")
            return
        
        for pos in positions:
            logger.info(f"Selling {pos.qty} of {pos.symbol} (market value: ${float(pos.market_value):.2f})")
            client.close_position(pos.symbol)
            logger.info(f"Position closed: {pos.symbol}")
        
        logger.info(f"All positions closed at {get_utc_now()}")
    except Exception as e:
        logger.error(f"Error selling positions: {e}")

def main():
    """Main function"""
    logger.info(f"Selling positions at {get_utc_now()}")
    
    try:
        client = TradeClient(
            api_key=os.getenv('ALPACA_KEY_ID'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        )
        
        sell_all_positions(client)
    except Exception as e:
        logger.error(f"Error connecting to Alpaca: {e}")
        logger.error("Make sure ALPACA_KEY_ID and ALPACA_SECRET_KEY are set correctly")

if __name__ == '__main__':
    main()

