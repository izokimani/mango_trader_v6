"""
Backtest script for sanity checking
"""
import os
import sys
from datetime import datetime
import importlib.util

sys.path.append(os.path.dirname(__file__))
from src.utils import get_db_connection, init_database, COINS
from scipy.stats import spearmanr
import numpy as np

def load_scorer():
    """Load the current scorer"""
    scorer_file = os.path.join(os.path.dirname(__file__), 'current_scorer.py')
    spec = importlib.util.spec_from_file_location("current_scorer", scorer_file)
    scorer_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer_module)
    return scorer_module.score_coin

def backtest(days=None):
    """Run backtest on historical data"""
    init_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if days:
        cursor.execute(f"""
            SELECT * FROM trades 
            WHERE actual_24h_return_of_chosen IS NOT NULL
            ORDER BY date DESC 
            LIMIT ?
        """, (days,))
    else:
        cursor.execute("""
            SELECT * FROM trades 
            WHERE actual_24h_return_of_chosen IS NOT NULL
            ORDER BY date DESC
        """)
    
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) == 0:
        print("No historical data found. Run the bot for a few days first.")
        return
    
    print(f"Backtesting on {len(rows)} days of data...")
    
    score_func = load_scorer()
    
    predicted_ranks = []
    actual_ranks = []
    daily_returns = []
    
    for row in rows:
        row_dict = dict(row)
        date = row_dict['date']
        
        # Score all coins
        scores = {}
        for coin in COINS:
            return_24h = row_dict.get(f'{coin}_return_24h', 0)
            return_6h = row_dict.get(f'{coin}_return_6h', 0)
            volume_ratio = row_dict.get(f'{coin}_volume_ratio', 1.0)
            news_sentiment = row_dict.get(f'{coin}_news_sentiment', 0.0)
            
            try:
                score = score_func(return_24h, return_6h, volume_ratio, news_sentiment)
                scores[coin] = score
            except Exception as e:
                print(f"Error scoring {coin} for {date}: {e}")
                scores[coin] = 0
        
        if not scores:
            continue
        
        # Get predicted coin
        predicted_coin = max(scores.items(), key=lambda x: x[1])[0]
        
        # Get actual returns
        actual_returns = {coin: row_dict.get(f'{coin}_return_24h', 0) for coin in COINS}
        sorted_actual = sorted(actual_returns.items(), key=lambda x: x[1], reverse=True)
        
        # Find predicted coin's actual rank
        predicted_rank = next((i+1 for i, (coin, _) in enumerate(sorted_actual) if coin == predicted_coin), 16)
        actual_rank = row_dict.get('rank_of_chosen', 16)
        
        predicted_ranks.append(predicted_rank)
        actual_ranks.append(actual_rank)
        
        # Get actual return
        actual_return = actual_returns.get(predicted_coin, 0)
        daily_returns.append(actual_return)
    
    # Calculate metrics
    correlation, _ = spearmanr(predicted_ranks, actual_ranks)
    avg_return = np.mean(daily_returns)
    sharpe_ratio = avg_return / np.std(daily_returns) if np.std(daily_returns) > 0 else 0
    win_rate = sum(1 for r in daily_returns if r > 0) / len(daily_returns) if daily_returns else 0
    
    print(f"\n=== Backtest Results ===")
    print(f"Days tested: {len(daily_returns)}")
    print(f"Average daily return: {avg_return:.2f}%")
    print(f"Sharpe ratio: {sharpe_ratio:.2f}")
    print(f"Win rate: {win_rate:.1%}")
    print(f"Rank correlation: {correlation:.4f}")
    print(f"Average predicted rank: {np.mean(predicted_ranks):.2f}")
    print(f"Average actual rank: {np.mean(actual_ranks):.2f}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, help='Number of days to backtest (default: all)')
    args = parser.parse_args()
    
    backtest(days=args.days)

