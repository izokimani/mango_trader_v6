"""
Flask web application for MangoTrades V6 Dashboard
Provides web interface to view analysis, metrics, trades, and logs
Works on both localhost and Render
"""
import os
import sys
import json
import glob
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, send_from_directory, request
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(__file__))

# Load environment variables
if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    load_dotenv()

from src.utils import get_db_connection, get_utc_now, format_date, COINS, init_database

app = Flask(__name__)

# Determine if running locally (for manual task triggers)
IS_LOCALHOST = os.getenv('RENDER') is None

# Initialize database on startup
try:
    init_database()
except Exception as e:
    print(f"Warning: Could not initialize database: {e}")

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', is_localhost=IS_LOCALHOST)

@app.route('/api/metrics')
def get_metrics():
    """Get overall performance metrics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Overall stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_trades,
            AVG(actual_24h_return_of_chosen) as avg_return,
            AVG(rank_of_chosen) as avg_rank,
            SUM(CASE WHEN actual_24h_return_of_chosen > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate,
            MAX(actual_24h_return_of_chosen) as best_return,
            MIN(actual_24h_return_of_chosen) as worst_return,
            MAX(model_version) as current_version
        FROM trades 
        WHERE actual_24h_return_of_chosen IS NOT NULL
    """)
    
    result = cursor.fetchone()
    overall = dict(result) if result else {
        'total_trades': 0,
        'avg_return': None,
        'avg_rank': None,
        'win_rate': None,
        'best_return': None,
        'worst_return': None,
        'current_version': None
    }
    
    # Recent trades (last 30 days)
    cursor.execute("""
        SELECT 
            date,
            chosen_coin,
            chosen_score,
            actual_24h_return_of_chosen,
            rank_of_chosen,
            model_version
        FROM trades 
        WHERE actual_24h_return_of_chosen IS NOT NULL
        ORDER BY date DESC
        LIMIT 30
    """)
    
    recent_trades = [dict(row) for row in cursor.fetchall()]
    
    # Model history
    cursor.execute("""
        SELECT date, version, improvement_type, spearman_correlation, avg_daily_return
        FROM model_history
        ORDER BY date DESC
        LIMIT 20
    """)
    
    model_history = [dict(row) for row in cursor.fetchall()]
    
    # Pending trades (predictions without results yet)
    cursor.execute("""
        SELECT date, chosen_coin, chosen_score, model_version
        FROM trades 
        WHERE actual_24h_return_of_chosen IS NULL
        ORDER BY date DESC
        LIMIT 5
    """)
    
    pending_trades = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'overall': overall,
        'recent_trades': recent_trades,
        'model_history': model_history,
        'pending_trades': pending_trades,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/trades')
def get_trades():
    """Get all trades with pagination"""
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            date,
            chosen_coin,
            chosen_score,
            actual_24h_return_of_chosen,
            rank_of_chosen,
            model_version
        FROM trades 
        ORDER BY date DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    trades = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT COUNT(*) FROM trades")
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'trades': trades,
        'total': total,
        'limit': limit,
        'offset': offset
    })

@app.route('/api/logs')
def get_logs():
    """Get recent log files"""
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        return jsonify({'logs': [], 'error': 'Log directory not found'})
    
    logs = []
    today = datetime.utcnow()
    
    for i in range(7):  # Last 7 days
        date = today - timedelta(days=i)
        log_file = os.path.join(log_dir, f"{date.strftime('%Y-%m-%d')}.log")
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    logs.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'content': content,
                        'lines': len(content.split('\n'))
                    })
            except Exception as e:
                logs.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'error': str(e)
                })
    
    return jsonify({'logs': logs})

@app.route('/api/analysis')
def get_analysis():
    """Get analysis reports"""
    analysis_dir = os.path.join(os.path.dirname(__file__), 'analysis')
    if not os.path.exists(analysis_dir):
        return jsonify({'reports': []})
    
    reports = []
    for file in glob.glob(os.path.join(analysis_dir, 'analysis_*.json')):
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                reports.append({
                    'date': data.get('date'),
                    'file': os.path.basename(file),
                    'metrics': data.get('metrics', {}),
                    'errors_count': len(data.get('errors', [])),
                    'warnings_count': len(data.get('warnings', []))
                })
        except Exception as e:
            reports.append({
                'file': os.path.basename(file),
                'error': str(e)
            })
    
    # Sort by date descending
    reports.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return jsonify({'reports': reports})

@app.route('/api/analysis/<filename>')
def get_analysis_file(filename):
    """Get specific analysis report"""
    analysis_dir = os.path.join(os.path.dirname(__file__), 'analysis')
    file_path = os.path.join(analysis_dir, filename)
    
    if not os.path.exists(file_path) or not filename.startswith('analysis_'):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        with open(file_path, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights/<filename>')
def get_insights_file(filename):
    """Get insights text file"""
    analysis_dir = os.path.join(os.path.dirname(__file__), 'analysis')
    file_path = os.path.join(analysis_dir, filename)
    
    if not os.path.exists(file_path) or not filename.startswith('insights_'):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        with open(file_path, 'r') as f:
            return jsonify({'content': f.read()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def get_health():
    """Get system health status"""
    issues = []
    
    # Check database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        issues.append(f"Database error: {e}")
        trade_count = 0
    
    # Check API keys
    required_keys = ['ALPACA_KEY_ID', 'ALPACA_SECRET_KEY', 'POLYGON_KEY', 'PERPLEXITY_KEY']
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        issues.append(f"Missing API keys: {', '.join(missing_keys)}")
    
    # Check log directory
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    log_files = len(glob.glob(os.path.join(log_dir, '*.log'))) if os.path.exists(log_dir) else 0
    
    # Check analysis directory
    analysis_dir = os.path.join(os.path.dirname(__file__), 'analysis')
    analysis_files = len(glob.glob(os.path.join(analysis_dir, '*.json'))) if os.path.exists(analysis_dir) else 0
    
    return jsonify({
        'status': 'healthy' if not issues else 'degraded',
        'issues': issues,
        'trade_count': trade_count,
        'log_files': log_files,
        'analysis_files': analysis_files,
        'is_localhost': IS_LOCALHOST
    })

@app.route('/api/run-task', methods=['POST'])
def run_task():
    """Run a task manually (only on localhost)"""
    if not IS_LOCALHOST:
        return jsonify({'error': 'Task execution only available on localhost'}), 403
    
    # Get JSON data safely (returns None if invalid/missing JSON)
    json_data = request.get_json(silent=True)
    if json_data is None:
        return jsonify({'error': 'Invalid or missing JSON in request body'}), 400
    
    task_name = json_data.get('task')
    if not task_name:
        return jsonify({'error': 'Missing "task" field in request body'}), 400
    
    if task_name not in ['fetch_data', 'sentiment', 'predict_and_trade', 'sell_position', 
                         'record_results', 'self_improve', 'self_analyze']:
        return jsonify({'error': 'Invalid task name'}), 400
    
    try:
        import subprocess
        script_dir = os.path.dirname(__file__)
        result = subprocess.run(
            ['bash', os.path.join(script_dir, 'run.sh'), task_name],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=script_dir
        )
        
        return jsonify({
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Default to port 5002 for localhost
    if IS_LOCALHOST:
        default_port = 5002
    else:
        default_port = 5000
    
    port = int(os.environ.get('PORT', default_port))
    print(f"\n{'='*60}")
    print(f"🚀 MangoTrades Dashboard starting...")
    print(f"📊 Access at: http://localhost:{port}")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=port, debug=IS_LOCALHOST)

