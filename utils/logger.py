import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger('BIS_BOT')

def log_request(user_id: int, username: str, command: str, status: str = "SUCCESS", data: dict = None):
    """Log a request made to the bot."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] User ID: {user_id} | Username: @{username} | Command: {command} | Status: {status}"
    
    # Add data if provided
    if data:
        log_message += f"\nData: {json.dumps(data, ensure_ascii=False, indent=2)}"
    
    logger.info(log_message)

def log_website_request(url: str, method: str, data: dict = None, response: dict = None):
    """Log website request and response data."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"\n{'='*50}\n[{timestamp}] Website Request:\nURL: {url}\nMethod: {method}"
    
    if data:
        log_message += f"\nRequest Data: {json.dumps(data, ensure_ascii=False, indent=2)}"
    
    if response:
        log_message += f"\nResponse Data: {json.dumps(response, ensure_ascii=False, indent=2)}"
    
    log_message += f"\n{'='*50}"
    logger.info(log_message) 