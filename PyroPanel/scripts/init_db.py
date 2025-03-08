#!/usr/bin/env python3
"""
Initialize the database with a default admin user.
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, SessionLocal
from app import models, schemas, crud
from app.auth import get_password_hash

def init_db(username, password, email):
    """Initialize the database with a default admin user."""
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    
    # Create admin user
    db = SessionLocal()
    try:
        # Check if user already exists
        db_user = crud.get_user_by_username(db, username=username)
        if db_user:
            print(f"User {username} already exists")
            return
        
        # Create user
        user_create = schemas.UserCreate(
            username=username,
            password=password,
            email=email,
            role="admin"
        )
        crud.create_user(db=db, user=user_create)
        print(f"Admin user {username} created successfully")
    finally:
        db.close()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize the database with a default admin user")
    parser.add_argument("--username", default="admin", help="Admin username")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--email", required=True, help="Admin email")
    
    args = parser.parse_args()
    
    init_db(args.username, args.password, args.email)

if __name__ == "__main__":
    main()
