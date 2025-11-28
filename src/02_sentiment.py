"""
Fetch news & social sentiment for all 16 coins from Polygon + Perplexity
Runs at 23:52 UTC daily
"""
import os
import sys
from datetime import datetime, timedelta
from polygon.rest import RESTClient
from openai import OpenAI
from dotenv import load_dotenv
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.utils import COINS, get_utc_now, get_logger

if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    load_dotenv()
logger = get_logger('sentiment')

def fetch_polygon_news(coin, hours=48):
    """Fetch news from Polygon for a coin"""
    client = RESTClient(os.getenv('POLYGON_KEY'))
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    try:
        # Get news for the coin
        # Polygon news API uses ticker format like "X:BTCUSD" for crypto
        polygon_ticker = f"X:{coin}" if not coin.startswith("X:") else coin
        news = client.list_ticker_news(
            ticker=polygon_ticker,
            limit=10,
            order='desc'
        )
        
        headlines = []
        for item in news:
            # Filter by date
            pub_date = datetime.fromtimestamp(item.published_utc / 1000)
            if pub_date >= start_time:
                headlines.append({
                    'title': item.title,
                    'description': item.description,
                    'published': pub_date.isoformat()
                })
        
        return headlines
    except Exception as e:
        logger.error(f"Error fetching news for {coin}: {e}")
        return []

def get_perplexity_summary(coin, headlines):
    """Get sentiment summary from Perplexity"""
    perplexity_key = os.getenv('PERPLEXITY_KEY')
    if not perplexity_key:
        logger.warning("PERPLEXITY_KEY not set, skipping Perplexity analysis")
        return None
    
    client = OpenAI(
        api_key=perplexity_key,
        base_url="https://api.perplexity.ai"
    )
    
    # Build prompt
    headlines_text = "\n".join([f"- {h['title']}" for h in headlines[:5]])
    
    prompt = f"""Analyze the sentiment and key drivers for {coin} based on these recent news headlines:

{headlines_text}

Provide a brief summary (2-3 sentences) of the sentiment and any significant developments. Rate overall sentiment from -1 (very bearish) to +1 (very bullish)."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-online",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        summary = response.choices[0].message.content
        return summary
    except Exception as e:
        logger.error(f"Error getting Perplexity summary for {coin}: {e}")
        return None

def calculate_sentiment_score(headlines, summary):
    """Calculate a sentiment score from -1 to +1"""
    if not headlines:
        return 0.0
    
    # Simple keyword-based sentiment
    positive_keywords = ['surge', 'rally', 'up', 'gain', 'bullish', 'breakthrough', 'launch', 'partnership', 'adoption']
    negative_keywords = ['crash', 'drop', 'down', 'loss', 'bearish', 'hack', 'ban', 'regulation', 'warning']
    
    score = 0.0
    for headline in headlines:
        text = (headline.get('title', '') + ' ' + headline.get('description', '')).lower()
        pos_count = sum(1 for word in positive_keywords if word in text)
        neg_count = sum(1 for word in negative_keywords if word in text)
        score += (pos_count - neg_count) * 0.1
    
    # Normalize to -1 to +1
    score = max(-1.0, min(1.0, score / len(headlines)))
    
    return score

def main():
    """Main function to fetch sentiment for all coins"""
    logger.info(f"Fetching sentiment at {get_utc_now()}")
    
    all_sentiment = {}
    all_headlines = {}
    all_summaries = {}
    
    for coin in COINS:
        logger.info(f"Fetching sentiment for {coin}...")
        
        # Get Polygon news
        headlines = fetch_polygon_news(coin, hours=48)
        all_headlines[coin] = headlines
        
        # Get Perplexity summary
        summary = get_perplexity_summary(coin, headlines)
        all_summaries[coin] = summary
        
        # Calculate sentiment score
        sentiment_score = calculate_sentiment_score(headlines, summary)
        all_sentiment[coin] = sentiment_score
        
        logger.info(f"{coin}: sentiment={sentiment_score:.3f}, headlines={len(headlines)}")
    
    # Save to JSON file
    output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sentiment_cache.json')
    with open(output_file, 'w') as f:
        json.dump({
            'sentiment': all_sentiment,
            'headlines': all_headlines,
            'summaries': all_summaries
        }, f, indent=2)
    
    logger.info(f"Sentiment data saved to {output_file}")

if __name__ == '__main__':
    main()

