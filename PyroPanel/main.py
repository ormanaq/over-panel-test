#!/usr/bin/env python3
"""
PyroPanel - A Python-based Game Server Management Panel

This is the main entry point for the PyroPanel application.
It provides a command-line interface to start the web panel or daemon.
"""

import argparse
import os
import sys
import uvicorn
import subprocess
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PyroPanel")

# Load environment variables
load_dotenv()

def start_web_panel(host="0.0.0.0", port=8000, reload=False):
    """Start the web panel"""
    logger.info(f"Starting PyroPanel web interface on {host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)

def start_daemon():
    """Start the server daemon"""
    logger.info("Starting PyroPanel daemon")
    daemon_path = os.path.join(os.path.dirname(__file__), "daemon", "daemon.py")
    
    # Check if daemon file exists
    if not os.path.exists(daemon_path):
        logger.error(f"Daemon file not found: {daemon_path}")
        sys.exit(1)
    
    # Start daemon process
    try:
        subprocess.run([sys.executable, daemon_path], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Daemon process failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")

def setup_database():
    """Set up the database"""
    from app.database import engine
    from app import models
    
    logger.info("Setting up database")
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database setup complete")

def create_admin_user(username, password, email):
    """Create an admin user"""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app import crud, schemas
    
    logger.info(f"Creating admin user: {username}")
    
    db = SessionLocal()
    try:
        # Check if user already exists
        db_user = crud.get_user_by_username(db, username=username)
        if db_user:
            logger.warning(f"User {username} already exists")
            return
        
        # Create user
        user_create = schemas.UserCreate(
            username=username,
            password=password,
            email=email,
            role="admin"
        )
        crud.create_user(db=db, user=user_create)
        logger.info(f"Admin user {username} created successfully")
    finally:
        db.close()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PyroPanel - Game Server Management Panel")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Web panel command
    web_parser = subparsers.add_parser("web", help="Start the web panel")
    web_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    web_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    web_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Start the server daemon")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up the application")
    setup_parser.add_argument("--admin-username", help="Admin username")
    setup_parser.add_argument("--admin-password", help="Admin password")
    setup_parser.add_argument("--admin-email", help="Admin email")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if args.command == "web":
        start_web_panel(args.host, args.port, args.reload)
    elif args.command == "daemon":
        start_daemon()
    elif args.command == "setup":
        setup_database()
        
        if args.admin_username and args.admin_password and args.admin_email:
            create_admin_user(args.admin_username, args.admin_password, args.admin_email)
        else:
            logger.info("No admin user created. To create an admin user, use --admin-username, --admin-password, and --admin-email")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
