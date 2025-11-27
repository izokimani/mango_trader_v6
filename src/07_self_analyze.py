"""
Daily Self-Analysis Module
Reads logs, analyzes performance, and generates insights for self-improvement
Runs at 00:25 UTC daily (after self-improvement)
"""
import os
import sys
import re
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import json
import glob

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.utils import get_db_connection, get_utc_now, format_date, get_logger, COINS

if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    load_dotenv()
logger = get_logger('self_analyze')

def read_recent_logs(days=7):
    """Read logs from the last N days"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(log_dir):
        logger.warning("Logs directory does not exist")
        return []
    
    logs = []
    today = datetime.utcnow()
    
    for i in range(days):
        date = today - timedelta(days=i)
        log_file = os.path.join(log_dir, f"{date.strftime('%Y-%m-%d')}.log")
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    logs.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'content': content
                    })
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
    
    return logs

def analyze_performance_metrics():
    """Analyze performance from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get recent performance
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
    
    # Get last 7 days performance
    cursor.execute("""
        SELECT 
            date,
            chosen_coin,
            actual_24h_return_of_chosen,
            rank_of_chosen,
            model_version
        FROM trades 
        WHERE actual_24h_return_of_chosen IS NOT NULL
        ORDER BY date DESC
        LIMIT 7
    """)
    
    recent_trades = cursor.fetchall()
    
    # Get model upgrade history
    cursor.execute("""
        SELECT date, version, improvement_type, spearman_correlation, avg_daily_return
        FROM model_history
        ORDER BY date DESC
        LIMIT 10
    """)
    
    model_history = cursor.fetchall()
    
    conn.close()
    
    return {
        'overall': dict(result) if result else {},
        'recent_trades': [dict(row) for row in recent_trades],
        'model_history': [dict(row) for row in model_history]
    }

def extract_errors_from_logs(logs):
    """Extract errors and warnings from logs"""
    errors = []
    warnings = []
    
    for log_entry in logs:
        content = log_entry['content']
        date = log_entry['date']
        
        # Find ERROR lines
        error_lines = re.findall(r'.*ERROR.*', content)
        for error in error_lines:
            errors.append({
                'date': date,
                'error': error.strip()
            })
        
        # Find WARNING lines
        warning_lines = re.findall(r'.*WARNING.*', content)
        for warning in warning_lines:
            warnings.append({
                'date': date,
                'warning': warning.strip()
            })
    
    return errors, warnings

def generate_daily_analysis():
    """Generate comprehensive daily analysis"""
    logger.info("Starting daily self-analysis...")
    
    # Read logs
    logs = read_recent_logs(days=7)
    logger.info(f"Read {len(logs)} days of logs")
    
    # Analyze performance
    metrics = analyze_performance_metrics()
    logger.info("Analyzed performance metrics")
    
    # Extract errors
    errors, warnings = extract_errors_from_logs(logs)
    logger.info(f"Found {len(errors)} errors and {len(warnings)} warnings")
    
    # Build analysis report
    report = {
        'date': format_date(get_utc_now()),
        'metrics': metrics,
        'errors': errors[:10],  # Last 10 errors
        'warnings': warnings[:10],  # Last 10 warnings
        'log_summary': {
            'days_analyzed': len(logs),
            'total_log_entries': sum(len(log['content'].split('\n')) for log in logs)
        }
    }
    
    # Save analysis report
    analysis_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'analysis')
    os.makedirs(analysis_dir, exist_ok=True)
    
    report_file = os.path.join(analysis_dir, f"analysis_{format_date(get_utc_now())}.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"Analysis report saved to {report_file}")
    
    # Generate insights using Perplexity
    generate_insights(report, metrics)
    
    return report

def generate_insights(report, metrics):
    """Use Perplexity to generate actionable insights"""
    perplexity_key = os.getenv('PERPLEXITY_KEY')
    if not perplexity_key:
        logger.warning("PERPLEXITY_KEY not set, skipping insight generation")
        return
    
    client = OpenAI(
        api_key=perplexity_key,
        base_url="https://api.perplexity.ai"
    )
    
    # Build prompt with performance data
    overall = metrics.get('overall', {})
    recent = metrics.get('recent_trades', [])
    
    prompt = f"""I am a crypto trading bot that trades daily. Here's my recent performance:

Overall Stats:
- Total trades: {overall.get('total_trades', 0)}
- Average daily return: {overall.get('avg_return', 0):.2f}%
- Average rank: {overall.get('avg_rank', 0):.1f}/16
- Win rate: {overall.get('win_rate', 0):.1f}%
- Best return: {overall.get('best_return', 0):.2f}%
- Worst return: {overall.get('worst_return', 0):.2f}%
- Current model version: {overall.get('current_version', 1)}

Last 7 Days:
"""
    
    for trade in recent[:7]:
        prompt += f"- {trade['date']}: {trade['chosen_coin']} → {trade['actual_24h_return_of_chosen']:.2f}% (Rank #{trade['rank_of_chosen']})\n"
    
    if report.get('errors'):
        prompt += f"\nRecent Errors ({len(report['errors'])}):\n"
        for error in report['errors'][:5]:
            prompt += f"- {error['date']}: {error['error']}\n"
    
    prompt += """
Analyze my performance and provide:
1. Key strengths and weaknesses
2. Patterns in successful vs unsuccessful trades
3. Specific recommendations for improvement
4. Any issues or errors that need attention

Be concise and actionable."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-sonar-small-128k-online",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        insights = response.choices[0].message.content
        
        # Save insights
        insights_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'analysis', 
            f"insights_{format_date(get_utc_now())}.txt"
        )
        
        with open(insights_file, 'w') as f:
            f.write(f"Daily Analysis Insights - {format_date(get_utc_now())}\n")
            f.write("=" * 60 + "\n\n")
            f.write(insights)
        
        logger.info(f"Insights saved to {insights_file}")
        logger.info("Key insights generated by Perplexity")
        
        # Log insights summary
        logger.info("\n" + "="*60)
        logger.info("PERPLEXITY INSIGHTS:")
        logger.info("="*60)
        for line in insights.split('\n')[:10]:  # First 10 lines
            if line.strip():
                logger.info(line)
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Error generating insights: {e}")

def check_system_health():
    """Check system health and log issues"""
    logger.info("Checking system health...")
    
    issues = []
    
    # Check database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        count = cursor.fetchone()[0]
        conn.close()
        logger.info(f"Database OK: {count} trades recorded")
    except Exception as e:
        issues.append(f"Database error: {e}")
        logger.error(f"Database check failed: {e}")
    
    # Check API keys
    required_keys = ['ALPACA_KEY_ID', 'ALPACA_SECRET_KEY', 'POLYGON_KEY', 'PERPLEXITY_KEY']
    missing_keys = []
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)
    
    if missing_keys:
        issues.append(f"Missing API keys: {', '.join(missing_keys)}")
        logger.warning(f"Missing API keys: {', '.join(missing_keys)}")
    else:
        logger.info("All API keys present")
    
    # Check log files
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if os.path.exists(log_dir):
        log_files = glob.glob(os.path.join(log_dir, '*.log'))
        logger.info(f"Log directory OK: {len(log_files)} log files")
    else:
        issues.append("Log directory does not exist")
        logger.warning("Log directory does not exist")
    
    if issues:
        logger.warning(f"System health check found {len(issues)} issues")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("System health check: All systems OK")
    
    return issues

def main():
    """Main self-analysis function"""
    logger.info("="*60)
    logger.info("DAILY SELF-ANALYSIS STARTING")
    logger.info("="*60)
    
    # System health check
    issues = check_system_health()
    
    # Generate analysis
    report = generate_daily_analysis()
    
    logger.info("="*60)
    logger.info("DAILY SELF-ANALYSIS COMPLETE")
    logger.info("="*60)
    
    # Summary
    metrics = report.get('metrics', {}).get('overall', {})
    logger.info(f"Summary: {metrics.get('total_trades', 0)} trades | "
                f"Avg Return: {metrics.get('avg_return', 0):.2f}% | "
                f"Win Rate: {metrics.get('win_rate', 0):.1f}% | "
                f"Model v{metrics.get('current_version', 1)}")

if __name__ == '__main__':
    main()

