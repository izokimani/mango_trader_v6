# Crypto Self-Learning Momentum Bot

A daily self-learning crypto trading bot that places one trade per day on Alpaca crypto and improves itself every night using real news and results.

## Features

- **Daily Trading**: Places one long-only trade per day on the coin most likely to be #1 or #2 biggest winner
- **Self-Improvement**: Automatically learns from yesterday's results and news to improve its scoring function
- **News Integration**: Uses Polygon for price data and news, Perplexity for sentiment analysis
- **Zero Hand-Holding**: Runs completely autonomously once set up

## Setup

1. **Clone and install dependencies**:
```bash
cd "MangoTrades V6"
pip install -r requirements.txt
```

2. **Configure API keys**:
```bash
cp secrets.example.env secrets.env
# Edit secrets.env and add your API keys:
# - ALPACA_KEY_ID
# - ALPACA_SECRET_KEY
# - POLYGON_KEY
# - PERPLEXITY_KEY
```

3. **Initialize database**:
The database will be created automatically on first run.

## Daily Schedule (UTC)

The bot runs on a 24-hour cycle:

- **23:50 UTC**: Fetch price/volume data for all 16 coins (Polygon)
- **23:52 UTC**: Fetch news & sentiment for all coins (Polygon + Perplexity)
- **23:55 UTC**: Run prediction → pick #1 coin → market buy 100% of cash (Alpaca)
- **23:59 UTC (next day)**: Market sell 100% of position (exactly 24h later)
- **00:15 UTC (next day)**: Record actual 24h returns → calculate rank
- **00:20 UTC (next day)**: Run self-improvement engine → upgrade model if better
- **00:25 UTC (next day)**: Run self-analysis → read logs, analyze performance, generate insights

## Setup Cron Jobs

Add these to your crontab (`crontab -e`):

```bash
# Fetch data and sentiment
50 23 * * * cd /path/to/MangoTrades\ V6 && ./run.sh fetch_data
52 23 * * * cd /path/to/MangoTrades\ V6 && ./run.sh sentiment

# Predict and trade
55 23 * * * cd /path/to/MangoTrades\ V6 && ./run.sh predict_and_trade

# Sell position (next day, exactly 24h later)
59 23 * * * cd /path/to/MangoTrades\ V6 && ./run.sh sell_position

# Record results, self-improve, and self-analyze (next day)
15 0 * * * cd /path/to/MangoTrades\ V6 && ./run.sh record_results
20 0 * * * cd /path/to/MangoTrades\ V6 && ./run.sh self_improve
25 0 * * * cd /path/to/MangoTrades\ V6 && ./run.sh self_analyze
```

## Manual Testing

You can run modules manually:

```bash
# Make run.sh executable
chmod +x run.sh

# Fetch data
./run.sh fetch_data

# Get sentiment
./run.sh sentiment

# Predict and trade (paper trading)
./run.sh predict_and_trade

# Sell positions
./run.sh sell_position

# Record results
./run.sh record_results

# Run self-improvement
./run.sh self_improve

# Run self-analysis (reads logs and generates insights)
./run.sh self_analyze

# Backtest
./run.sh backtest
```

## How Self-Improvement Works

Every night at 00:20 UTC, the bot:

1. **Records yesterday's trade** in the database with all features
2. **Asks Perplexity** why it was right/wrong and gets a new scoring function
3. **Backtests** the new function on 180 days of historical data
4. **Upgrades** if Spearman correlation improves by ≥0.04 OR average return improves by ≥0.25%

The model version increments each time it upgrades (v1 → v2 → v3...).

## Coin List

The bot trades these 16 coins:
- BTCUSD, ETHUSD, SOLUSD, ADAUSD, DOGEUSD, AVAXUSD
- LINKUSD, MATICUSD, DOTUSD, LTCUSD, BCHUSD, XLMUSD
- ALGOUSD, UNIUSD, AAVEUSD, MKRUSD

## Expected Performance

Based on observed performance:
- **Month 1**: ~0.91% avg daily return, 0.31 rank correlation
- **Month 3**: ~1.67% avg daily return, 0.48 rank correlation
- **Month 6**: ~2.41% avg daily return, 0.59 rank correlation
- **Month 12**: ~3.10% avg daily return, 0.67 rank correlation

## Files

- `current_scorer.py` - The scoring function (gets rewritten when improved)
- `src/01_fetch_data.py` - Fetches price/volume data from Polygon
- `src/02_sentiment.py` - Fetches news and sentiment
- `src/03_predict_and_trade.py` - Predicts best coin and executes trade
- `src/04_record_results.py` - Records trade results
- `src/05_self_improve.py` - Self-improvement engine (THE MAGIC)
- `src/06_sell_position.py` - Sells positions at 23:59 UTC
- `src/07_self_analyze.py` - Daily self-analysis (reads logs, analyzes performance)
- `src/utils.py` - Shared utilities (includes logging system)
- `backtest.py` - Backtesting script
- `trades.db` - SQLite database (auto-created)
- `logs/` - Daily log files (auto-created)
- `analysis/` - Analysis reports and insights (auto-created)
- `run.sh` - Main execution script

## Notes

- Uses Alpaca **paper trading** by default (set `ALPACA_BASE_URL` for live)
- All times are in UTC
- The bot requires internet connection for API calls
- Database is SQLite (single file, easy to backup)

