from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Text, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# Association table for many-to-many relationship between users and servers
user_server_association = Table(
    'user_server_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('server_id', Integer, ForeignKey('servers.id'))
)

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")  # admin, user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owned_servers = relationship("Server", back_populates="owner")
    accessible_servers = relationship(
        "Server",
        secondary=user_server_association,
        back_populates="users_with_access"
    )
    api_keys = relationship("ApiKey", back_populates="user")

class Server(Base):
    """Game server model"""
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    game_type = Column(String, index=True)  # minecraft, valheim, etc.
    image = Column(String)  # Docker image
    status = Column(String, default="stopped")  # running, stopped, error
    
    # Server configuration
    memory_limit = Column(Integer)  # MB
    cpu_limit = Column(Float)  # CPU cores
    disk_limit = Column(Integer)  # MB
    
    # Network configuration
    port = Column(Integer)
    ip_address = Column(String, nullable=True)
    
    # Docker container ID
    container_id = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Owner relationship
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="owned_servers")
    
    # Users with access
    users_with_access = relationship(
        "User",
        secondary=user_server_association,
        back_populates="accessible_servers"
    )
    
    # Server variables
    variables = relationship("ServerVariable", back_populates="server")
    
    # Backups
    backups = relationship("Backup", back_populates="server")

class ServerVariable(Base):
    """Environment variables for game servers"""
    __tablename__ = "server_variables"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String)
    value = Column(String)
    
    # Server relationship
    server_id = Column(Integer, ForeignKey("servers.id"))
    server = relationship("Server", back_populates="variables")

class ApiKey(Base):
    """API keys for programmatic access"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="api_keys")

class Backup(Base):
    """Server backups"""
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    path = Column(String)
    size = Column(Integer)  # Size in bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Server relationship
    server_id = Column(Integer, ForeignKey("servers.id"))
    server = relationship("Server", back_populates="backups")
