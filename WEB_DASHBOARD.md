# MangoTrades V6 Web Dashboard

A modern web interface to view and manage your MangoTrades V6 trading bot.

## Features

- **Performance Metrics**: View overall trading statistics, win rate, average returns, and more
- **Recent Trades**: See your last 30 trades with detailed information
- **Pending Trades**: View trades that are waiting for results
- **Model History**: Track model upgrades and improvements over time
- **Analysis Reports**: Browse and view detailed analysis reports
- **Logs Viewer**: Real-time log viewing with color-coded entries
- **System Health**: Monitor system status and API key configuration
- **Manual Task Runner** (localhost only): Manually trigger bot tasks

## Running Locally

1. **Install dependencies** (if not already done):
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the web server**:
   ```bash
   python app.py
   ```

3. **Open your browser**:
   Navigate to `http://localhost:5000`

The dashboard will automatically refresh every 30 seconds to show the latest data.

## Running on Render

The dashboard is configured in `render.yaml` as a web service. When deployed:

1. The dashboard will be available at your Render service URL
2. Manual task execution is disabled for security (only available on localhost)
3. The dashboard will automatically detect it's running on Render

## API Endpoints

The dashboard uses these API endpoints:

- `GET /api/health` - System health status
- `GET /api/metrics` - Performance metrics and recent trades
- `GET /api/trades` - All trades (with pagination)
- `GET /api/logs` - Recent log files
- `GET /api/analysis` - List of analysis reports
- `GET /api/analysis/<filename>` - Specific analysis report
- `POST /api/run-task` - Run a task manually (localhost only)

## Manual Task Execution (Localhost Only)

When running locally, you can manually trigger bot tasks:

1. Select a task from the dropdown (e.g., "Fetch Data", "Predict & Trade")
2. Click "Run Task"
3. View the output in real-time
4. The dashboard will automatically refresh after task completion

Available tasks:
- `fetch_data` - Fetch price/volume data
- `sentiment` - Get sentiment analysis
- `predict_and_trade` - Predict best coin and execute trade
- `sell_position` - Sell current position
- `record_results` - Record trade results
- `self_improve` - Run self-improvement engine
- `self_analyze` - Generate analysis report

## Troubleshooting

**Dashboard shows "No trades recorded yet"**
- This is normal if the bot hasn't completed any trades yet
- Run the trading cycle manually or wait for scheduled jobs

**Can't access dashboard on Render**
- Check that the web service is deployed and running
- Verify the PORT environment variable is set (Render sets this automatically)
- Check Render logs for any errors

**Manual tasks not working**
- Manual task execution only works on localhost
- On Render, tasks run automatically via the scheduler

## Architecture

- **Backend**: Flask (Python)
- **Frontend**: Vanilla JavaScript (no frameworks)
- **Styling**: Modern CSS with gradient design
- **Data**: SQLite database (trades.db)
- **Logs**: Daily log files in `logs/` directory
- **Analysis**: JSON reports in `analysis/` directory

## Security Notes

- Manual task execution is disabled on Render for security
- API endpoints are read-only (except `/api/run-task` which is localhost-only)
- No authentication is implemented (add if deploying publicly)

