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

class FriendRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class User(Base):
    """User model"""
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    gender = Column(SQLEnum(Gender), nullable=True)  # NEW: Gender field
    selected_size = Column(String(10), nullable=True)  # NEW: User's preferred size
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    favorite_brands = relationship("UserBrand", back_populates="user", cascade="all, delete-orphan")
    favorite_styles = relationship("UserStyle", back_populates="user", cascade="all, delete-orphan")
    
    # Friend relationships
    sent_friend_requests = relationship("FriendRequest", foreign_keys="FriendRequest.sender_id", back_populates="sender", cascade="all, delete-orphan")
    received_friend_requests = relationship("FriendRequest", foreign_keys="FriendRequest.recipient_id", back_populates="recipient", cascade="all, delete-orphan")
    friendships = relationship("Friendship", foreign_keys="Friendship.user_id", back_populates="user", cascade="all, delete-orphan")
    friends = relationship("Friendship", foreign_keys="Friendship.friend_id", back_populates="friend", cascade="all, delete-orphan")

class OAuthAccount(Base):
    """OAuth account model for social login"""
    __tablename__ = "oauth_accounts"
    __table_args__ = {"extend_existing": True}
    
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
    __table_args__ = {"extend_existing": True}
    
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

class Category(Base):
    """Category model for products"""
    __tablename__ = "categories"

    id = Column(String(50), primary_key=True) # e.g., "dresses", "shirts"
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserBrand(Base):
    """User-Brand many-to-many relationship"""
    __tablename__ = "user_brands"
    __table_args__ = {"extend_existing": True}
    
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
    __table_args__ = {"extend_existing": True}
    
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

class ProductStyle(Base):
    """Product-Style many-to-many association table"""
    __tablename__ = "product_styles"
    __table_args__ = {"extend_existing": True}

    product_id = Column(String, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    style_id = Column(String(50), ForeignKey("styles.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="styles")
    style = relationship("Style", back_populates="products")


class Product(Base):
    """Product model for recommendations"""
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    price = Column(String(50), nullable=False) # Storing as string to include currency symbol
    image_url = Column(String(500), nullable=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    category_id = Column(String(50), ForeignKey("categories.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    brand = relationship("Brand")
    category = relationship("Category")
    styles = relationship("ProductStyle", back_populates="product", cascade="all, delete-orphan")

class UserLikedProduct(Base):
    """User-Product many-to-many relationship for liked items"""
    __tablename__ = "user_liked_products"
    __table_args__ = {"extend_existing": True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(String, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="liked_products")
    product = relationship("Product")
    
    __table_args__ = (
        # Unique constraint to prevent duplicate user-product relationships
    )

# Add liked_products relationship to User model
User.liked_products = relationship("UserLikedProduct", back_populates="user", cascade="all, delete-orphan")

class FriendRequest(Base):
    """Friend request model"""
    __tablename__ = "friend_requests"
    __table_args__ = {"extend_existing": True}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLEnum(FriendRequestStatus), default=FriendRequestStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_friend_requests")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_friend_requests")
    
    # Ensure unique sender-recipient combinations
    __table_args__ = (
        # Unique constraint to prevent duplicate friend requests
    )

class Friendship(Base):
    """Friendship model for accepted friend relationships"""
    __tablename__ = "friendships"
    __table_args__ = {"extend_existing": True}
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    friend_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="friendships")
    friend = relationship("User", foreign_keys=[friend_id], back_populates="friends")
    
    # Ensure unique user-friend combinations
    __table_args__ = (
        # Unique constraint to prevent duplicate friendships
    )

# Add products relationship to Style model
Style.products = relationship("ProductStyle", back_populates="style", cascade="all, delete-orphan") 