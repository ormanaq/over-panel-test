from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app import models, schemas
from app.auth import get_password_hash, verify_password

# User CRUD operations
def get_user(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    """Get user by username"""
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get list of users"""
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    """Create new user"""
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user: schemas.UserCreate):
    """Update user"""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.username = user.username
        db_user.email = user.email
        db_user.full_name = user.full_name
        db_user.role = user.role
        
        if user.password:
            db_user.hashed_password = get_password_hash(user.password)
        
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    """Delete user"""
    db_user = get_user(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user with username and password"""
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# Server CRUD operations
def get_server(db: Session, server_id: int):
    """Get server by ID"""
    return db.query(models.Server).filter(models.Server.id == server_id).first()

def get_servers(db: Session, skip: int = 0, limit: int = 100):
    """Get list of all servers"""
    return db.query(models.Server).offset(skip).limit(limit).all()

def get_user_servers(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get servers owned by or accessible to a user"""
    return db.query(models.Server).filter(
        (models.Server.owner_id == user_id) | 
        (models.Server.users_with_access.any(models.User.id == user_id))
    ).offset(skip).limit(limit).all()

def create_server(db: Session, server: schemas.ServerCreate, user_id: int):
    """Create new server"""
    db_server = models.Server(
        name=server.name,
        description=server.description,
        game_type=server.game_type,
        image=server.image,
        memory_limit=server.memory_limit,
        cpu_limit=server.cpu_limit,
        disk_limit=server.disk_limit,
        port=server.port,
        owner_id=user_id
    )
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    
    # Add server variables if provided
    if server.variables:
        for var in server.variables:
            db_var = models.ServerVariable(
                key=var.key,
                value=var.value,
                server_id=db_server.id
            )
            db.add(db_var)
        db.commit()
        db.refresh(db_server)
    
    return db_server

def update_server(db: Session, server_id: int, server: schemas.ServerCreate):
    """Update server"""
    db_server = get_server(db, server_id)
    if db_server:
        db_server.name = server.name
        db_server.description = server.description
        db_server.game_type = server.game_type
        db_server.image = server.image
        db_server.memory_limit = server.memory_limit
        db_server.cpu_limit = server.cpu_limit
        db_server.disk_limit = server.disk_limit
        db_server.port = server.port
        
        db.commit()
        db.refresh(db_server)
        
        # Update variables if provided
        if server.variables:
            # Delete existing variables
            db.query(models.ServerVariable).filter(
                models.ServerVariable.server_id == server_id
            ).delete()
            
            # Add new variables
            for var in server.variables:
                db_var = models.ServerVariable(
                    key=var.key,
                    value=var.value,
                    server_id=db_server.id
                )
                db.add(db_var)
            
            db.commit()
            db.refresh(db_server)
    
    return db_server

def delete_server(db: Session, server_id: int):
    """Delete server"""
    db_server = get_server(db, server_id)
    if db_server:
        # Delete associated variables
        db.query(models.ServerVariable).filter(
            models.ServerVariable.server_id == server_id
        ).delete()
        
        # Delete associated backups
        db.query(models.Backup).filter(
            models.Backup.server_id == server_id
        ).delete()
        
        # Delete server
        db.delete(db_server)
        db.commit()
    
    return db_server

def add_user_to_server(db: Session, server_id: int, user_id: int):
    """Grant user access to server"""
    db_server = get_server(db, server_id)
    db_user = get_user(db, user_id)
    
    if db_server and db_user:
        db_server.users_with_access.append(db_user)
        db.commit()
        db.refresh(db_server)
    
    return db_server

def remove_user_from_server(db: Session, server_id: int, user_id: int):
    """Revoke user access to server"""
    db_server = get_server(db, server_id)
    db_user = get_user(db, user_id)
    
    if db_server and db_user and db_user in db_server.users_with_access:
        db_server.users_with_access.remove(db_user)
        db.commit()
        db.refresh(db_server)
    
    return db_server

# API Key CRUD operations
def create_api_key(db: Session, api_key: schemas.ApiKeyCreate, user_id: int):
    """Create new API key"""
    import secrets
    
    # Generate random API key
    key = secrets.token_hex(16)
    
    db_api_key = models.ApiKey(
        key=key,
        description=api_key.description,
        user_id=user_id
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    return db_api_key

def get_api_keys(db: Session, user_id: int):
    """Get API keys for a user"""
    return db.query(models.ApiKey).filter(models.ApiKey.user_id == user_id).all()

def delete_api_key(db: Session, api_key_id: int):
    """Delete API key"""
    db_api_key = db.query(models.ApiKey).filter(models.ApiKey.id == api_key_id).first()
    
    if db_api_key:
        db.delete(db_api_key)
        db.commit()
    
    return db_api_key

# Backup CRUD operations
def create_backup(db: Session, backup: schemas.BackupCreate, server_id: int):
    """Create new backup"""
    db_backup = models.Backup(
        name=backup.name,
        path=backup.path,
        size=backup.size,
        server_id=server_id
    )
    
    db.add(db_backup)
    db.commit()
    db.refresh(db_backup)
    
    return db_backup

def get_backups(db: Session, server_id: int):
    """Get backups for a server"""
    return db.query(models.Backup).filter(models.Backup.server_id == server_id).all()

def delete_backup(db: Session, backup_id: int):
    """Delete backup"""
    db_backup = db.query(models.Backup).filter(models.Backup.id == backup_id).first()
    
    if db_backup:
        db.delete(db_backup)
        db.commit()
    
    return db_backup
