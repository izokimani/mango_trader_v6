"""
Self-Improvement Engine – runs Steps 1-4 every night at 00:20 UTC
This is THE MAGIC – makes tomorrow's brain smarter
"""
import os
import sys
import re
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from scipy.stats import spearmanr
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.utils import get_db_connection, get_utc_now, format_date, init_database, get_logger

if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    load_dotenv()
logger = get_logger('self_improve')

def get_yesterday_trade_data():
    """Get yesterday's trade data from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    yesterday = format_date(get_utc_now() - timedelta(days=1))
    
    cursor.execute("SELECT * FROM trades WHERE date = ?", (yesterday,))
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None

def get_all_returns_yesterday():
    """Get actual 24h returns for all coins yesterday"""
    from src.utils import COINS
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    yesterday = format_date(get_utc_now() - timedelta(days=1))
    
    cursor.execute("SELECT * FROM trades WHERE date = ?", (yesterday,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None
    
    returns = {}
    for coin in COINS:
        col_name = f"{coin}_return_24h"
        returns[coin] = result[col_name] if col_name in result.keys() else 0.0
    
    return returns

def ask_perplexity_why_right_wrong(yesterday_data):
    """Step 2: Ask Perplexity why we were right/wrong"""
    perplexity_key = os.getenv('PERPLEXITY_KEY')
    if not perplexity_key:
        logger.warning("PERPLEXITY_KEY not set, skipping Perplexity analysis")
        return None
    
    client = OpenAI(
        api_key=perplexity_key,
        base_url="https://api.perplexity.ai"
    )
    
    from src.utils import COINS
    
    # Build returns string
    returns_str = "\n".join([f"{coin}: {yesterday_data.get(f'{coin}_return_24h', 0):.2f}%" for coin in COINS])
    
    chosen_coin = yesterday_data.get('chosen_coin', 'UNKNOWN')
    actual_return = yesterday_data.get('actual_24h_return_of_chosen', 0)
    rank = yesterday_data.get('rank_of_chosen', 16)
    
    # Get news headlines
    headlines = yesterday_data.get('news_headlines', '')
    
    prompt = f"""Here are the actual 24-hour returns of 16 cryptos yesterday:
{returns_str}

We picked {chosen_coin} because it had the highest momentum + volume score.
The actual return was {actual_return:.2f}%, ranking #{rank} out of 16.

Top 5 news headlines yesterday that mentioned {chosen_coin}:
{headlines}

Explain in plain English what actually drove the #1 and #2 biggest movers yesterday.
Then write a short Python scoring function (max 10 lines) that would have ranked the #1 coin first and the worst coin last.
Only use features we already calculate (past returns, volume, RSI, news sentiment).

The function signature must be:
def score_coin(return_24h, return_6h, volume_ratio, news_sentiment):
    # your code here
    return score

Return ONLY the Python function code, nothing else."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-online",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        
        # Extract Python function code
        code_match = re.search(r'def score_coin\([^)]+\):.*?return\s+\w+', answer, re.DOTALL)
        if code_match:
            return code_match.group(0)
        else:
            # Try to find function in code blocks
            code_block = re.search(r'```python\n(.*?)\n```', answer, re.DOTALL)
            if code_block:
                return code_block.group(1)
            return answer
    except Exception as e:
        logger.error(f"Error asking Perplexity: {e}")
        return None

def backtest_scorer(scorer_code, days=180):
    """Step 3: Backtest the new scoring function"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get last N days of data
    cursor.execute(f"""
        SELECT * FROM trades 
        WHERE actual_24h_return_of_chosen IS NOT NULL
        ORDER BY date DESC 
        LIMIT ?
    """, (days,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 10:
        logger.warning(f"Not enough historical data ({len(rows)} rows), need at least 10")
        return None, None
    
    # Execute the scorer code in a safe namespace
    namespace = {}
    try:
        exec(scorer_code, namespace)
        score_func = namespace.get('score_coin')
        if not score_func:
            logger.error("Error: score_coin function not found in code")
            return None, None
    except Exception as e:
        logger.error(f"Error executing scorer code: {e}")
        return None, None
    
    from src.utils import COINS
    
    # Calculate predictions and actual ranks for each day
    # For Spearman: compare predicted ranking (by score) vs actual ranking (by return)
    all_predicted_ranks = []  # List of lists: predicted ranking of all coins each day
    all_actual_ranks = []      # List of lists: actual ranking of all coins each day
    daily_returns = []         # Return of the top predicted coin each day
    
    for row in rows:
        row_dict = dict(row)
        date = row_dict['date']
        
        # Score all coins for this day
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
                logger.error(f"Error scoring {coin} for {date}: {e}")
                scores[coin] = 0
        
        if not scores:
            continue
        
        # Get predicted coin (highest score)
        predicted_coin = max(scores.items(), key=lambda x: x[1])[0]
        
        # Get actual returns for this day
        actual_returns = {coin: row_dict.get(f'{coin}_return_24h', 0) for coin in COINS}
        
        # Rank coins by predicted score (1 = highest score)
        sorted_by_score = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        predicted_ranking = {coin: i+1 for i, (coin, _) in enumerate(sorted_by_score)}
        
        # Rank coins by actual return (1 = highest return)
        sorted_by_return = sorted(actual_returns.items(), key=lambda x: x[1], reverse=True)
        actual_ranking = {coin: i+1 for i, (coin, _) in enumerate(sorted_by_return)}
        
        # Store rankings for Spearman correlation
        predicted_ranks_for_day = [predicted_ranking[coin] for coin in COINS]
        actual_ranks_for_day = [actual_ranking[coin] for coin in COINS]
        
        all_predicted_ranks.extend(predicted_ranks_for_day)
        all_actual_ranks.extend(actual_ranks_for_day)
        
        # Get actual return of predicted coin
        actual_return = actual_returns.get(predicted_coin, 0)
        daily_returns.append(actual_return)
    
    if len(all_predicted_ranks) < 10:
        return None, None
    
    # Calculate Spearman correlation: how well do predicted ranks match actual ranks?
    correlation, _ = spearmanr(all_predicted_ranks, all_actual_ranks)
    
    # Calculate average daily return
    avg_return = np.mean(daily_returns)
    
    return correlation, avg_return

def get_current_performance():
    """Get current model performance"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            AVG(actual_24h_return_of_chosen) as avg_return,
            COUNT(*) as count
        FROM trades 
        WHERE actual_24h_return_of_chosen IS NOT NULL
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result['count'] > 0:
        return result['avg_return'], result['count']
    return None, 0

def get_current_scorer_code():
    """Get current scorer code"""
    scorer_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'current_scorer.py')
    if os.path.exists(scorer_file):
        with open(scorer_file, 'r') as f:
            return f.read()
    return None

def get_current_model_version():
    """Get current model version from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(model_version) as max_version FROM trades")
    result = cursor.fetchone()
    conn.close()
    
    return result['max_version'] if result and result['max_version'] else 1

def upgrade_model(new_scorer_code, correlation, avg_return, improvement_type):
    """Upgrade the model by replacing current_scorer.py"""
    scorer_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'current_scorer.py')
    
    # Backup old version
    if os.path.exists(scorer_file):
        backup_file = scorer_file + f".backup.v{get_current_model_version()}"
        with open(scorer_file, 'r') as f:
            old_code = f.read()
        with open(backup_file, 'w') as f:
            f.write(old_code)
    
    # Write new version
    new_version = get_current_model_version() + 1
    
    # Ensure the code is properly formatted
    if not new_scorer_code.strip().startswith('def'):
        # Try to extract just the function
        func_match = re.search(r'def score_coin\([^)]+\):.*?return\s+\w+', new_scorer_code, re.DOTALL)
        if func_match:
            new_scorer_code = func_match.group(0)
    
    with open(scorer_file, 'w') as f:
        f.write(f"# Version {new_version} – auto-upgraded by self-improvement engine\n")
        f.write(new_scorer_code)
        if not new_scorer_code.endswith('\n'):
            f.write('\n')
    
    # Record in model_history
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO model_history (date, version, scorer_code, spearman_correlation, avg_daily_return, improvement_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (format_date(get_utc_now()), new_version, new_scorer_code, correlation, avg_return, improvement_type))
    
    conn.commit()
    conn.close()
    
    logger.info(f"MODEL UPGRADED – v{new_version-1} → v{new_version}")
    logger.info(f"  Correlation: {correlation:.4f}")
    logger.info(f"  Avg Return: {avg_return:.2f}%")
    logger.info(f"  Improvement: {improvement_type}")

def long_term_improvement():
    """Step 4: Long-term memory improvement (every 30 days)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if we have 30+ days of data
    cursor.execute("SELECT COUNT(*) as count FROM trades WHERE actual_24h_return_of_chosen IS NOT NULL")
    result = cursor.fetchone()
    conn.close()
    
    if not result or result['count'] < 30:
        logger.info("Not enough data for long-term improvement (need 30+ days)")
        return
    
    # Get all trade data
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE actual_24h_return_of_chosen IS NOT NULL ORDER BY date")
    rows = cursor.fetchall()
    conn.close()
    
    # Build prompt for Perplexity
    perplexity_key = os.getenv('PERPLEXITY_KEY')
    if not perplexity_key:
        return
    
    client = OpenAI(
        api_key=perplexity_key,
        base_url="https://api.perplexity.ai"
    )
    
    # Summarize performance
    total_trades = len(rows)
    avg_return = np.mean([dict(row)['actual_24h_return_of_chosen'] for row in rows])
    
    prompt = f"""Here are {total_trades} daily crypto trades with what we predicted vs what actually happened.
Average daily return: {avg_return:.2f}%

Write the single best Python scoring function (max 15 lines) that would have produced the highest Sharpe ratio.
Only use features we already calculate (past returns, volume, RSI, news sentiment).

The function signature must be:
def score_coin(return_24h, return_6h, volume_ratio, news_sentiment):
    # your code here
    return score

Return ONLY the Python function code, nothing else."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-online",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        
        # Extract function code
        code_match = re.search(r'def score_coin\([^)]+\):.*?return\s+\w+', answer, re.DOTALL)
        if code_match:
            scorer_code = code_match.group(0)
        else:
            code_block = re.search(r'```python\n(.*?)\n```', answer, re.DOTALL)
            scorer_code = code_block.group(1) if code_block else answer
        
        # Backtest
        correlation, avg_return_new = backtest_scorer(scorer_code, days=180)
        
        if correlation is None:
            return
        
        # Get current performance
        current_corr, _ = backtest_scorer(get_current_scorer_code(), days=180)
        current_avg, _ = get_current_performance()
        
        if current_corr is None or current_avg is None:
            return
        
        # Check if improvement
        corr_improvement = correlation - current_corr if current_corr else 0
        return_improvement = avg_return_new - current_avg if current_avg else 0
        
        if corr_improvement >= 0.04 or return_improvement >= 0.25:
            upgrade_model(scorer_code, correlation, avg_return_new, "long_term")
    except Exception as e:
        logger.error(f"Error in long-term improvement: {e}")

def main():
    """Main self-improvement function"""
    logger.info(f"Running self-improvement engine at {get_utc_now()}")
    
    # Initialize database if needed
    init_database()
    
    # Step 1: Yesterday's data should already be in database (from 04_record_results.py)
    yesterday_data = get_yesterday_trade_data()
    
    if not yesterday_data:
        logger.warning("No yesterday's data found. Make sure 04_record_results.py ran first.")
        return
    
    logger.info("Step 1: Yesterday's data already in database ✓")
    
    # Step 2: Ask Perplexity why we were right/wrong
    logger.info("Step 2: Asking Perplexity for insights...")
    new_scorer_code = ask_perplexity_why_right_wrong(yesterday_data)
    
    if not new_scorer_code:
        logger.warning("Could not get new scorer code from Perplexity")
        return
    
    logger.info("Got new scorer code from Perplexity")
    
    # Step 3: Backtest the new idea
    logger.info("Step 3: Backtesting new scorer...")
    correlation, avg_return = backtest_scorer(new_scorer_code, days=180)
    
    if correlation is None:
        logger.error("Backtest failed")
        return
    
    logger.info(f"New scorer performance: correlation={correlation:.4f}, avg_return={avg_return:.2f}%")
    
    # Get current performance
    current_scorer_code = get_current_scorer_code()
    if current_scorer_code:
        current_corr, _ = backtest_scorer(current_scorer_code, days=180)
        current_avg, _ = get_current_performance()
        
        if current_corr is None:
            current_corr = 0.0
        if current_avg is None:
            current_avg = 0.0
        
        corr_improvement = correlation - current_corr
        return_improvement = avg_return - current_avg
        
        logger.info(f"Current performance: correlation={current_corr:.4f}, avg_return={current_avg:.2f}%")
        logger.info(f"Improvement: correlation +{corr_improvement:.4f}, return +{return_improvement:.2f}%")
        
        # Check if improvement threshold met
        if corr_improvement >= 0.04 or return_improvement >= 0.25:
            logger.info("✓ Improvement threshold met! Upgrading model...")
            upgrade_model(new_scorer_code, correlation, avg_return, "daily")
        else:
            logger.info(f"✗ Improvement not significant enough (need +0.04 correlation or +0.25% return)")
    else:
        # First time, always upgrade
        logger.info("First scorer, upgrading...")
        upgrade_model(new_scorer_code, correlation, avg_return, "initial")
    
    # Step 4: Long-term improvement (every 30 days)
    logger.info("Step 4: Checking for long-term improvement...")
    days_since_start = (get_utc_now() - datetime(2024, 1, 1)).days
    if days_since_start % 30 == 0:
        long_term_improvement()
    else:
        logger.info("Skipping long-term improvement (runs every 30 days)")
    
    logger.info("Self-improvement cycle complete!")

if __name__ == '__main__':
    main()

