# Deploying to Render

This guide will help you deploy the MangoTrades bot to Render.

## Step 1: Connect Your Repository

1. Go to your Render dashboard
2. Click "New" → "Blueprint"
3. Connect your GitHub/GitLab repository
4. Render will detect `render.yaml` automatically

## Step 2: Set Environment Variables

In Render dashboard, go to your service → Environment → Add Environment Variable:

**Required Variables:**
- `ALPACA_KEY_ID` - Your Alpaca API key ID
- `ALPACA_SECRET_KEY` - Your Alpaca secret key
- `ALPACA_BASE_URL` - `https://paper-api.alpaca.markets` (for paper trading)
- `POLYGON_KEY` - Your Polygon API key
- `PERPLEXITY_KEY` - Your Perplexity API key

**Optional (if you have them):**
- `SEC_API_KEY` - SEC API key (if using)
- `GOOGLE_API_KEY` - Google API key (if using)
- `GOOGLE_CSE_ID` - Google Custom Search Engine ID (if using)

## Step 3: Deploy

Render will automatically:
1. Install dependencies from `requirements.txt`
2. Start the scheduler service
3. Run all scheduled tasks automatically

## How It Works on Render

- **Scheduler Service**: Runs `scheduler.py` which uses APScheduler instead of cron
- **All tasks run automatically** at their scheduled UTC times:
  - 23:50 UTC - Fetch data
  - 23:52 UTC - Fetch sentiment
  - 23:55 UTC - Predict and trade
  - 23:59 UTC - Sell position
  - 00:15 UTC - Record results
  - 00:20 UTC - Self-improve
  - 00:25 UTC - Self-analyze

## Monitoring

- **Logs**: View logs in Render dashboard under your service
- **Database**: SQLite database is stored in persistent disk (survives restarts)
- **Analysis Reports**: Saved to `analysis/` directory

## Troubleshooting

1. **Service won't start**: Check logs for import errors or missing dependencies
2. **Tasks not running**: Verify scheduler is running and check logs
3. **API errors**: Verify all environment variables are set correctly
4. **Database issues**: Check that persistent disk is mounted

## Local Testing

Before deploying, test locally:
```bash
# Install dependencies
pip install -r requirements.txt

# Test scheduler
python scheduler.py

# Or test individual modules
./run.sh fetch_data
./run.sh sentiment
./run.sh predict_and_trade
```

## Notes

- The bot uses **paper trading** by default (set via `ALPACA_BASE_URL`)
- All times are in **UTC**
- The scheduler runs continuously and executes jobs at scheduled times
- Database and logs persist across deployments
