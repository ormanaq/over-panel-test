from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import schemas, crud
from app.database import get_db

router = APIRouter()

@router.get("/", response_model=list[schemas.Server])
async def read_servers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get list of servers"""
    return crud.get_servers(db, skip=skip, limit=limit)

@router.post("/", response_model=schemas.Server)
async def create_server(server: schemas.ServerCreate, db: Session = Depends(get_db)):
    """Create a new server"""
    return crud.create_server(db=db, server=server)

@router.get("/{server_id}", response_model=schemas.Server)
async def read_server(server_id: int, db: Session = Depends(get_db)):
    """Get server by ID"""
    db_server = crud.get_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return db_server

@router.put("/{server_id}", response_model=schemas.Server)
async def update_server(server_id: int, server: schemas.ServerCreate, db: Session = Depends(get_db)):
    """Update a server"""
    return crud.update_server(db=db, server_id=server_id, server=server)

@router.delete("/{server_id}", response_model=schemas.Server)
async def delete_server(server_id: int, db: Session = Depends(get_db)):
    """Delete a server"""
    return crud.delete_server(db=db, server_id=server_id)
