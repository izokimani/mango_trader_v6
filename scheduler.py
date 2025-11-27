"""
Scheduler for Render deployment - runs all tasks on schedule
Replaces cron jobs with APScheduler for cloud deployment
"""
import os
import sys
import traceback
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(__file__))

# Load environment variables (from secrets.env or Render env vars)
if os.path.exists('secrets.env'):
    load_dotenv('secrets.env')
else:
    # On Render, env vars are already set, just load dotenv for defaults
    load_dotenv()

from src.utils import get_logger, init_database

logger = get_logger('scheduler')

def run_task(task_name):
    """Run a task by directly importing and calling the module"""
    logger.info(f"Running task: {task_name}")
    
    try:
        # Initialize database if needed
        init_database()
        
        # Import modules dynamically
        if task_name == 'fetch_data':
            import importlib.util
            spec = importlib.util.spec_from_file_location("module", os.path.join(os.path.dirname(__file__), "src", "01_fetch_data.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        elif task_name == 'sentiment':
            import importlib.util
            spec = importlib.util.spec_from_file_location("module", os.path.join(os.path.dirname(__file__), "src", "02_sentiment.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        elif task_name == 'predict_and_trade':
            import importlib.util
            spec = importlib.util.spec_from_file_location("module", os.path.join(os.path.dirname(__file__), "src", "03_predict_and_trade.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        elif task_name == 'sell_position':
            import importlib.util
            spec = importlib.util.spec_from_file_location("module", os.path.join(os.path.dirname(__file__), "src", "06_sell_position.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        elif task_name == 'record_results':
            import importlib.util
            spec = importlib.util.spec_from_file_location("module", os.path.join(os.path.dirname(__file__), "src", "04_record_results.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        elif task_name == 'self_improve':
            import importlib.util
            spec = importlib.util.spec_from_file_location("module", os.path.join(os.path.dirname(__file__), "src", "05_self_improve.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        elif task_name == 'self_analyze':
            import importlib.util
            spec = importlib.util.spec_from_file_location("module", os.path.join(os.path.dirname(__file__), "src", "07_self_analyze.py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            logger.error(f"Unknown task: {task_name}")
            return
        
        # Run the main function
        module.main()
        logger.info(f"Task {task_name} completed successfully")
        
    except Exception as e:
        logger.error(f"Error running task {task_name}: {e}")
        logger.error(traceback.format_exc())

def main():
    """Setup and run scheduler"""
    logger.info("Starting MangoTrades scheduler...")
    
    # Initialize database on startup
    logger.info("Initializing database...")
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        logger.error(traceback.format_exc())
    
    scheduler = BlockingScheduler(timezone='UTC')
    
    # Daily schedule (all times UTC)
    # 23:50 - Fetch data
    scheduler.add_job(
        lambda: run_task('fetch_data'),
        CronTrigger(hour=23, minute=50),
        id='fetch_data',
        name='Fetch price/volume data'
    )
    
    # 23:52 - Fetch sentiment
    scheduler.add_job(
        lambda: run_task('sentiment'),
        CronTrigger(hour=23, minute=52),
        id='sentiment',
        name='Fetch sentiment data'
    )
    
    # 23:55 - Predict and trade
    scheduler.add_job(
        lambda: run_task('predict_and_trade'),
        CronTrigger(hour=23, minute=55),
        id='predict_and_trade',
        name='Predict and execute trade'
    )
    
    # 23:59 next day - Sell position (24h after buy)
    # Note: This runs at 23:59 UTC daily, which is 24h after the 23:55 buy
    scheduler.add_job(
        lambda: run_task('sell_position'),
        CronTrigger(hour=23, minute=59),
        id='sell_position',
        name='Sell position after 24h'
    )
    
    # 00:15 next day - Record results
    scheduler.add_job(
        lambda: run_task('record_results'),
        CronTrigger(hour=0, minute=15),
        id='record_results',
        name='Record trade results'
    )
    
    # 00:20 next day - Self improve
    scheduler.add_job(
        lambda: run_task('self_improve'),
        CronTrigger(hour=0, minute=20),
        id='self_improve',
        name='Self-improvement engine'
    )
    
    logger.info("Scheduler configured. Jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} ({job.id}): {job.next_run_time}")
    
    logger.info("Scheduler running... Press Ctrl+C to exit")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")

if __name__ == '__main__':
    main()

