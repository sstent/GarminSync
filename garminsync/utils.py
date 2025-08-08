import logging
import sys
from datetime import datetime

# Configure logging
def setup_logger(name="garminsync", level=logging.INFO):
    """Setup logger with consistent formatting"""
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

# Create default logger instance
logger = setup_logger()

def format_timestamp(timestamp_str=None):
    """Format timestamp string for display"""
    if not timestamp_str:
        return "Never"
    
    try:
        # Parse ISO format timestamp
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return timestamp_str

def safe_filename(filename):
    """Make filename safe for filesystem"""
    import re
    # Replace problematic characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Replace spaces and colons commonly found in timestamps
    safe_name = safe_name.replace(':', '-').replace(' ', '_')
    return safe_name

def bytes_to_human_readable(bytes_count):
    """Convert bytes to human readable format"""
    if bytes_count == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} TB"

def validate_cron_expression(cron_expr):
    """Basic validation of cron expression"""
    try:
        from apscheduler.triggers.cron import CronTrigger
        # Try to create a CronTrigger with the expression
        CronTrigger.from_crontab(cron_expr)
        return True
    except (ValueError, TypeError):
        return False

# Utility function for error handling
def handle_db_error(func):
    """Decorator for database operations with error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database operation failed in {func.__name__}: {e}")
            raise
    return wrapper