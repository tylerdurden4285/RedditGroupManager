#!/usr/bin/env python3
import os
import sys
import threading
import signal
import logging
import uvicorn

from dotenv import load_dotenv


from reddit_manager import create_app
from reddit_manager.utils.logging import setup_logging
from reddit_manager.utils.db import init_db
from api_main import app as fastapi_app


load_dotenv()


setup_logging()
logger = logging.getLogger(__name__)


DEFAULT_FRONTEND_HOST = "0.0.0.0"
DEFAULT_FRONTEND_PORT = 5015
DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 8015




def init_database():
    """
    Initialize and migrate the database if needed
    """
    try:
        logger.info("Initializing database...")
        
        
        init_db()
        logger.info("Database initialization complete")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def run_api():
    """
    Run the FastAPI backend server
    """
    
    host = os.getenv('API_HOST', DEFAULT_API_HOST)
    port = int(os.getenv('API_PORT', DEFAULT_API_PORT))
    
    logger.info(f"Starting API server on http://{host}:{port}")
    print(f"\033[36m[API] Starting on http://{host}:{port}\033[0m")
    
    
    uvicorn.run(
        fastapi_app,
        host=host,
        port=port,
        reload=False,  
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )


def handle_exit(signum, frame):
    logger.info("Shutting down services...")
    print("\n\033[33m[Runner] Shutting down services...\033[0m")
    sys.exit(0)
    
if __name__ == '__main__':
    
    if not init_database():
        logger.error("Database initialization failed. Exiting.")
        sys.exit(1)
    
    
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    logger.info("Starting Reddit Group Manager application")
    
    
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        print("\033[32m[Runner] API server started in background\033[0m")
    
    
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    
    host = os.getenv('FRONTEND_HOST', DEFAULT_FRONTEND_HOST)
    port = int(os.getenv('FRONTEND_PORT', DEFAULT_FRONTEND_PORT))
    max_port_attempts = 10  
    
    
    def is_port_in_use(host, port):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return False
            except OSError:
                return True
    
    
    original_port = port
    for attempt in range(max_port_attempts):
        if is_port_in_use(host, port):
            print(f"Port {port} is already in use. Trying port {port + 1}...")
            port += 1
            if attempt == max_port_attempts - 1:
                print(f"Couldn't find an available port after {max_port_attempts} attempts.")
                print("Please free up a port or specify a different port using the FRONTEND_PORT environment variable.")
                sys.exit(1)
        else:
            
            if port != original_port:
                print(f"Found available port: {port}")
            
            print(f"\033[35m[Frontend] Starting on http://{host}:{port}\033[0m")
            print("\033[33m[Runner] Press Ctrl+C to stop all services\033[0m")
            
            app.run(
                host=host,
                port=port,
                debug=True,
                use_reloader=True,
                use_debugger=True,
                threaded=True
            )
            break
