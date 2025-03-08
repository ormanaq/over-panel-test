from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    servers = relationship("Server", back_populates="owner")

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    game_type = Column(String, index=True)
    status = Column(String, default="stopped")  # running, stopped, error
    port = Column(Integer)
    memory_limit = Column(Integer)  # in MB
    cpu_limit = Column(Float)  # percentage
    owner_id = Column(Integer, ForeignKey("users.id"))
    container_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_started = Column(DateTime, nullable=True)
    
    owner = relationship("User", back_populates="servers")
