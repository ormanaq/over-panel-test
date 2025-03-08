from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Base schemas
class ServerVariableBase(BaseModel):
    key: str
    value: str

class ServerVariableCreate(ServerVariableBase):
    pass

class ServerVariable(ServerVariableBase):
    id: int
    server_id: int

    class Config:
        orm_mode = True

class BackupBase(BaseModel):
    name: str
    path: str
    size: int

class BackupCreate(BackupBase):
    pass

class Backup(BackupBase):
    id: int
    server_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class ApiKeyBase(BaseModel):
    description: Optional[str] = None

class ApiKeyCreate(ApiKeyBase):
    pass

class ApiKey(ApiKeyBase):
    id: int
    key: str
    user_id: int
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "user"

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class UserInDB(User):
    hashed_password: str

# Server schemas
class ServerBase(BaseModel):
    name: str
    description: Optional[str] = None
    game_type: str
    image: str
    memory_limit: int = Field(..., description="Memory limit in MB")
    cpu_limit: float = Field(..., description="CPU limit in cores")
    disk_limit: int = Field(..., description="Disk limit in MB")
    port: int

class ServerCreate(ServerBase):
    variables: Optional[List[ServerVariableCreate]] = None

class Server(ServerBase):
    id: int
    status: str
    ip_address: Optional[str] = None
    container_id: Optional[str] = None
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    variables: List[ServerVariable] = []
    backups: List[Backup] = []

    class Config:
        orm_mode = True

# Server action schema
class ServerAction(BaseModel):
    action: str = Field(..., description="Action to perform: start, stop, restart")

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Stats schemas
class ServerStats(BaseModel):
    cpu_usage: float
    memory_usage: int
    disk_usage: int
    uptime: int  # in seconds
    player_count: Optional[int] = None

# Dashboard schemas
class DashboardStats(BaseModel):
    total_servers: int
    active_servers: int
    total_users: int
    system_load: float
