"""
Authentication service for user operations and OAuth integration
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import User, OAuthAccount
from oauth_service import oauth_service
from config import settings
import bcrypt
import jwt
from datetime import datetime, timedelta
import uuid

class AuthService:
    """Authentication service for user operations"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """Verify JWT token and return user ID"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            return user_id
        except jwt.PyJWTError:
            return None
    
    @staticmethod
    def create_user(
        db: Session,
        username: str,
        email: str,
        password_hash: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        is_verified: bool = False
    ) -> User:
        """Create a new user"""
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            is_verified=is_verified,
            is_profile_complete=bool(first_name and last_name)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_oauth_account(db: Session, provider: str, provider_user_id: str) -> Optional[OAuthAccount]:
        """Get OAuth account by provider and provider user ID"""
        return db.query(OAuthAccount).filter(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id
        ).first()
    
    @staticmethod
    def create_oauth_account(
        db: Session,
        user_id: str,
        provider: str,
        provider_user_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> OAuthAccount:
        """Create a new OAuth account"""
        oauth_account = OAuthAccount(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        db.add(oauth_account)
        db.commit()
        db.refresh(oauth_account)
        return oauth_account
    
    @staticmethod
    def update_oauth_account(
        db: Session,
        oauth_account: OAuthAccount,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> OAuthAccount:
        """Update OAuth account tokens"""
        if access_token:
            oauth_account.access_token = access_token
        if refresh_token:
            oauth_account.refresh_token = refresh_token
        if expires_at:
            oauth_account.expires_at = expires_at
        
        oauth_account.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(oauth_account)
        return oauth_account
    
    @staticmethod
    async def handle_oauth_login(db: Session, provider: str, token: str) -> Optional[Dict[str, Any]]:
        """Handle OAuth login for a specific provider"""
        user_info = None
        
        # Get user info from provider
        if provider == 'google':
            user_info = await oauth_service.get_google_user_info(token)
        elif provider == 'facebook':
            user_info = await oauth_service.get_facebook_user_info(token)
        elif provider == 'github':
            user_info = await oauth_service.get_github_user_info(token)
        elif provider == 'apple':
            user_info = await oauth_service.verify_apple_token(token)
        
        if not user_info:
            return None
        
        # Check if OAuth account already exists
        oauth_account = AuthService.get_oauth_account(
            db, provider, user_info['provider_user_id']
        )
        
        if oauth_account:
            # Update existing OAuth account
            AuthService.update_oauth_account(db, oauth_account, access_token=token)
            user = oauth_account.user
        else:
            # Check if user exists with same email
            user = AuthService.get_user_by_email(db, user_info['email'])
            
            if user:
                # Create OAuth account for existing user
                AuthService.create_oauth_account(
                    db, user.id, provider, user_info['provider_user_id'], token
                )
            else:
                # Create new user and OAuth account
                username = AuthService._generate_unique_username(db, user_info)
                user = AuthService.create_user(
                    db=db,
                    username=username,
                    email=user_info['email'],
                    first_name=user_info['first_name'],
                    last_name=user_info['last_name'],
                    avatar_url=user_info['avatar_url'],
                    is_verified=user_info['is_verified']
                )
                
                AuthService.create_oauth_account(
                    db, user.id, provider, user_info['provider_user_id'], token
                )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        
        return {
            "token": access_token,
            "expires_at": datetime.utcnow() + access_token_expires,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "avatar_url": user.avatar_url,
                "is_profile_complete": user.is_profile_complete,
                "is_verified": user.is_verified,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }
    
    @staticmethod
    def _generate_unique_username(db: Session, user_info: Dict[str, Any]) -> str:
        """Generate a unique username from user info"""
        base_username = user_info.get('first_name', '').lower() or user_info.get('email', '').split('@')[0]
        base_username = ''.join(c for c in base_username if c.isalnum() or c in '_-')
        
        if not base_username:
            base_username = 'user'
        
        username = base_username
        counter = 1
        
        while AuthService.get_user_by_username(db, username):
            username = f"{base_username}{counter}"
            counter += 1
        
        return username

# Create auth service instance
auth_service = AuthService() 