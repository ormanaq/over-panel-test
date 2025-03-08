from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Server schemas
class ServerBase(BaseModel):
    name: str
    game_type: str
    port: int
    memory_limit: int
    cpu_limit: float

class ServerCreate(ServerBase):
    pass

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    port: Optional[int] = None
    memory_limit: Optional[int] = None
    cpu_limit: Optional[float] = None

class Server(ServerBase):
    id: int
    status: str
    owner_id: int
    container_id: Optional[str]
    created_at: datetime
    last_started: Optional[datetime]

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Server Status schemas
class ServerStats(BaseModel):
    cpu_usage: float
    memory_usage: int
    uptime: int
    status: str

class ServerCommand(BaseModel):
    command: str  # start, stop, restart
