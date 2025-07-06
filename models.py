"""
Database models for PolkaAPI
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from enum import Enum
from datetime import datetime

Base = declarative_base()

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"

class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    gender = Column(SQLEnum(Gender), nullable=True)  # NEW: Gender field
    selected_size = Column(String(10), nullable=True)  # NEW: User's preferred size
    avatar_url = Column(String(500), nullable=True)
    is_profile_complete = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    favorite_brands = relationship("UserBrand", back_populates="user", cascade="all, delete-orphan")
    favorite_styles = relationship("UserStyle", back_populates="user", cascade="all, delete-orphan")

class OAuthAccount(Base):
    """OAuth account model for social login"""
    __tablename__ = "oauth_accounts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)  # google, facebook, github, apple
    provider_user_id = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="oauth_accounts")
    
    # Composite unique constraint
    __table_args__ = (
        # Ensure one OAuth account per provider per user
        # and one user per provider_user_id per provider
    )

class Brand(Base):
    """Brand model"""
    __tablename__ = "brands"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    logo = Column(String(500), nullable=True)
    description = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Style(Base):
    """Style model"""
    __tablename__ = "styles"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    image = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserBrand(Base):
    """User-Brand many-to-many relationship"""
    __tablename__ = "user_brands"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="favorite_brands")
    brand = relationship("Brand")
    
    # Ensure unique user-brand combinations
    __table_args__ = (
        # Unique constraint to prevent duplicate user-brand relationships
    )

class UserStyle(Base):
    """User-Style many-to-many relationship"""
    __tablename__ = "user_styles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    style_id = Column(String(50), ForeignKey("styles.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="favorite_styles")
    style = relationship("Style")
    
    # Ensure unique user-style combinations
    __table_args__ = (
        # Unique constraint to prevent duplicate user-style relationships
    ) 