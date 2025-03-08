from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import os

# Import local modules
from app import models, schemas, crud
from app.database import engine, get_db
from app.auth import create_access_token, get_current_user, get_password_hash, verify_password
from app.server_routes import router as server_router
from app.server_routes import router as server_router

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="PyroPanel",
    description="A Python-based game server management panel",
    version="0.1.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Render the home page"""
    return templates.TemplateResponse("index.html", {"request": request, "title": "PyroPanel"})

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Server routes
@app.get("/servers/", response_model=List[schemas.Server])
async def read_servers(
    skip: int = 0, 
    limit: int = 100, 
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of servers"""
    if current_user.role != "admin":
        servers = crud.get_user_servers(db, user_id=current_user.id, skip=skip, limit=limit)
    else:
        servers = crud.get_servers(db, skip=skip, limit=limit)
    return servers

@app.post("/servers/", response_model=schemas.Server)
async def create_server(
    server: schemas.ServerCreate, 
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new server"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return crud.create_server(db=db, server=server, user_id=current_user.id)

@app.get("/servers/{server_id}", response_model=schemas.Server)
async def read_server(
    server_id: int, 
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get server details"""
    server = crud.get_server(db, server_id=server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Check if user has access to this server
    if current_user.role != "admin" and server.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return server

@app.post("/servers/{server_id}/action")
async def server_action(
    server_id: int,
    action: schemas.ServerAction,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform action on server (start, stop, restart)"""
    server = crud.get_server(db, server_id=server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Check if user has access to this server
    if current_user.role != "admin" and server.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # TODO: Implement actual server control logic via daemon
    if action.action == "start":
        return {"status": "success", "message": f"Server {server_id} started"}
    elif action.action == "stop":
        return {"status": "success", "message": f"Server {server_id} stopped"}
    elif action.action == "restart":
        return {"status": "success", "message": f"Server {server_id} restarted"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

# User routes
@app.post("/users/", response_model=schemas.User)
async def create_user(
    user: schemas.UserCreate, 
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    return crud.create_user(db=db, user=user)

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
