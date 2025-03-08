from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import docker
from datetime import datetime

from .. import models, schemas
from ..database import get_db
from .auth import get_current_user

router = APIRouter()
docker_client = docker.from_env()

def get_server_stats(container_id: str) -> schemas.ServerStats:
    try:
        container = docker_client.containers.get(container_id)
        stats = container.stats(stream=False)
        
        # Calculate CPU usage
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                   stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                      stats['precpu_stats']['system_cpu_usage']
        cpu_usage = (cpu_delta / system_delta) * 100.0
        
        # Calculate memory usage
        memory_usage = stats['memory_stats']['usage']
        
        # Calculate uptime
        uptime = (datetime.now() - 
                 datetime.fromtimestamp(stats['read'].timestamp())).seconds
        
        return schemas.ServerStats(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            uptime=uptime,
            status=container.status
        )
    except docker.errors.NotFound:
        raise HTTPException(
            status_code=404,
            detail="Container not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting server stats: {str(e)}"
        )

@router.post("/", response_model=schemas.Server)
def create_server(
    server: schemas.ServerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if port is available
    existing_server = db.query(models.Server).filter(
        models.Server.port == server.port
    ).first()
    if existing_server:
        raise HTTPException(
            status_code=400,
            detail="Port already in use"
        )
    
    db_server = models.Server(
        **server.dict(),
        owner_id=current_user.id
    )
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server

@router.get("/", response_model=List[schemas.Server])
def list_servers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    servers = db.query(models.Server).filter(
        models.Server.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    return servers

@router.get("/{server_id}", response_model=schemas.Server)
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    server = db.query(models.Server).filter(
        models.Server.id == server_id,
        models.Server.owner_id == current_user.id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server

@router.get("/{server_id}/stats", response_model=schemas.ServerStats)
def get_server_statistics(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    server = db.query(models.Server).filter(
        models.Server.id == server_id,
        models.Server.owner_id == current_user.id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    if not server.container_id:
        raise HTTPException(status_code=400, detail="Server not running")
    
    return get_server_stats(server.container_id)

@router.post("/{server_id}/command")
async def send_server_command(
    server_id: int,
    command: schemas.ServerCommand,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    server = db.query(models.Server).filter(
        models.Server.id == server_id,
        models.Server.owner_id == current_user.id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        if command.command == "start":
            if server.container_id:
                raise HTTPException(status_code=400, detail="Server already running")
            
            container = docker_client.containers.run(
                f"gameserver/{server.game_type}",
                detach=True,
                ports={f"{server.port}/tcp": server.port},
                mem_limit=f"{server.memory_limit}m",
                cpu_period=100000,
                cpu_quota=int(server.cpu_limit * 100000)
            )
            
            server.container_id = container.id
            server.status = "running"
            server.last_started = datetime.utcnow()
            
        elif command.command == "stop":
            if not server.container_id:
                raise HTTPException(status_code=400, detail="Server not running")
            
            container = docker_client.containers.get(server.container_id)
            container.stop()
            container.remove()
            
            server.container_id = None
            server.status = "stopped"
            
        elif command.command == "restart":
            if not server.container_id:
                raise HTTPException(status_code=400, detail="Server not running")
            
            container = docker_client.containers.get(server.container_id)
            container.restart()
            
            server.status = "running"
            server.last_started = datetime.utcnow()
            
        else:
            raise HTTPException(status_code=400, detail="Invalid command")
        
        db.commit()
        return {"status": "success", "message": f"Server {command.command} command executed"}
        
    except docker.errors.ImageNotFound:
        raise HTTPException(
            status_code=400,
            detail=f"Game server image for {server.game_type} not found"
        )
    except docker.errors.APIError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Docker API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing command: {str(e)}"
        )

@router.delete("/{server_id}")
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    server = db.query(models.Server).filter(
        models.Server.id == server_id,
        models.Server.owner_id == current_user.id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if server.container_id:
        try:
            container = docker_client.containers.get(server.container_id)
            container.stop()
            container.remove()
        except docker.errors.NotFound:
            pass
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error stopping server: {str(e)}"
            )

    db.delete(server)
    db.commit()
    return {"status": "success", "message": "Server deleted"}
