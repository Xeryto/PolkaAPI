from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import re

# Import our modules
from config import settings
from database import get_db, init_db
from models import User, OAuthAccount, Brand, Style, UserBrand, UserStyle, Gender
from auth_service import auth_service
from oauth_service import oauth_service

app = FastAPI(
    title="PolkaAPI - Authentication Backend",
    description="A modern, fast, and secure authentication API with OAuth support for mobile and web applications",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for React Native app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < settings.MIN_USERNAME_LENGTH:
            raise ValueError(f'Username must be at least {settings.MIN_USERNAME_LENGTH} characters')
        if ' ' in v:
            raise ValueError('Username cannot contain spaces')
        if not v.replace('_', '').replace('-', '').replace('#', '').replace('$', '').replace('!', '').isalnum():
            raise ValueError('Username contains invalid characters')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < settings.MIN_PASSWORD_LENGTH:
            raise ValueError(f'Password must be at least {settings.MIN_PASSWORD_LENGTH} characters')
        if ' ' in v:
            raise ValueError('Password cannot contain spaces')
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError('Password must contain both letters and numbers')
        return v

class UserLogin(BaseModel):
    identifier: str  # Can be either email or username
    password: str
    
    @validator('identifier')
    def validate_identifier(cls, v):
        if not v or not v.strip():
            raise ValueError('Identifier cannot be empty')
        return v.strip()
    
    def is_email(self) -> bool:
        """Check if the identifier is an email address"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, self.identifier))
    
    def is_username(self) -> bool:
        """Check if the identifier is a username"""
        # Username pattern: alphanumeric, underscores, hyphens, #, $, !
        username_pattern = r'^[a-zA-Z0-9_\-#$!]+$'
        return bool(re.match(username_pattern, self.identifier)) and not self.is_email()

class OAuthLogin(BaseModel):
    provider: str  # google, facebook, github, apple
    token: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_profile_complete: bool = False
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime

class AuthResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserResponse

class OAuthProviderResponse(BaseModel):
    provider: str
    client_id: str
    redirect_url: str
    scope: str

class TokenData(BaseModel):
    user_id: Optional[str] = None

class UserProfileUpdate(BaseModel):
    gender: Optional[Gender] = None
    selected_size: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class BrandResponse(BaseModel):
    id: int
    name: str
    slug: str
    logo: Optional[str] = None
    description: Optional[str] = None

class StyleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    image: Optional[str] = None

class UserBrandsUpdate(BaseModel):
    brand_ids: List[int]

class UserStylesUpdate(BaseModel):
    style_ids: List[str]

class EnhancedUserResponse(BaseModel):
    id: str
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[Gender] = None
    selected_size: Optional[str] = None
    avatar_url: Optional[str] = None
    is_profile_complete: bool = False
    is_verified: bool = False
    favorite_brands: List[BrandResponse] = []
    favorite_styles: List[StyleResponse] = []
    created_at: datetime
    updated_at: datetime

# Dependency to get current user
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    user_id = auth_service.verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# API Endpoints
@app.post("/api/v1/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    if auth_service.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    if auth_service.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    password_hash = auth_service.hash_password(user_data.password)
    user = auth_service.create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return AuthResponse(
        token=access_token,
        expires_at=datetime.utcnow() + access_token_expires,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            avatar_url=user.avatar_url,
            is_profile_complete=user.is_profile_complete,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    )

@app.post("/api/v1/auth/login", response_model=AuthResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user with email or username and password"""
    
    # Determine if the identifier is an email or username
    if user_data.is_email():
        user = auth_service.get_user_by_email(db, user_data.identifier)
    elif user_data.is_username():
        user = auth_service.get_user_by_username(db, user_data.identifier)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid identifier format. Please provide a valid email or username."
        )
    
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not auth_service.verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return AuthResponse(
        token=access_token,
        expires_at=datetime.utcnow() + access_token_expires,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            avatar_url=user.avatar_url,
            is_profile_complete=user.is_profile_complete,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    )

@app.post("/api/v1/auth/oauth/login", response_model=AuthResponse)
async def oauth_login(oauth_data: OAuthLogin, db: Session = Depends(get_db)):
    """Login with OAuth provider"""
    result = await auth_service.handle_oauth_login(db, oauth_data.provider, oauth_data.token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth token or provider not supported"
        )
    
    return AuthResponse(
        token=result["token"],
        expires_at=result["expires_at"],
        user=UserResponse(**result["user"])
    )

@app.get("/api/v1/auth/oauth/providers", response_model=List[OAuthProviderResponse])
async def get_oauth_providers():
    """Get available OAuth providers"""
    providers = []
    
    if settings.GOOGLE_CLIENT_ID:
        providers.append(OAuthProviderResponse(
            provider="google",
            client_id=settings.GOOGLE_CLIENT_ID,
            redirect_url=f"{settings.OAUTH_REDIRECT_URL}/google",
            scope="openid email profile"
        ))
    
    if settings.FACEBOOK_CLIENT_ID:
        providers.append(OAuthProviderResponse(
            provider="facebook",
            client_id=settings.FACEBOOK_CLIENT_ID,
            redirect_url=f"{settings.OAUTH_REDIRECT_URL}/facebook",
            scope="email public_profile"
        ))
    
    if settings.GITHUB_CLIENT_ID:
        providers.append(OAuthProviderResponse(
            provider="github",
            client_id=settings.GITHUB_CLIENT_ID,
            redirect_url=f"{settings.OAUTH_REDIRECT_URL}/github",
            scope="read:user user:email"
        ))
    
    if settings.APPLE_CLIENT_ID:
        providers.append(OAuthProviderResponse(
            provider="apple",
            client_id=settings.APPLE_CLIENT_ID,
            redirect_url=f"{settings.OAUTH_REDIRECT_URL}/apple",
            scope="name email"
        ))
    
    return providers

@app.get("/api/v1/auth/oauth/{provider}/authorize")
async def oauth_authorize(provider: str, request: Request):
    """Redirect to OAuth provider authorization URL"""
    oauth_client = oauth_service.get_oauth_client(provider)
    
    if not oauth_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth provider not configured"
        )
    
    redirect_uri = f"{settings.OAUTH_REDIRECT_URL}/{provider}"
    authorization_url, state = oauth_client.create_authorization_url(
        redirect_uri=redirect_uri
    )
    
    return RedirectResponse(url=authorization_url)

@app.get("/api/v1/auth/oauth/callback/{provider}")
async def oauth_callback(provider: str, code: str, state: str, db: Session = Depends(get_db)):
    """Handle OAuth callback"""
    oauth_client = oauth_service.get_oauth_client(provider)
    
    if not oauth_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth provider not configured"
        )
    
    try:
        redirect_uri = f"{settings.OAUTH_REDIRECT_URL}/{provider}"
        token = oauth_client.fetch_token(
            token_url=oauth_client.token_endpoint,
            authorization_response=f"?code={code}&state={state}",
            redirect_uri=redirect_uri
        )
        
        access_token = token.get('access_token')
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token"
            )
        
        result = await auth_service.handle_oauth_login(db, provider, access_token)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process OAuth login"
            )
        
        # In a real application, you might want to redirect to a frontend URL
        # with the token as a query parameter or use a more sophisticated approach
        return {
            "token": result["token"],
            "expires_at": result["expires_at"],
            "user": result["user"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}"
        )

@app.post("/api/v1/auth/logout")
async def logout():
    """Logout user (JWT tokens are stateless)"""
    return {"message": "Successfully logged out"}

@app.get("/api/v1/user/profile", response_model=EnhancedUserResponse)
async def get_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's complete profile"""
    # Get favorite brands and styles
    favorite_brands = db.query(UserBrand).filter(UserBrand.user_id == current_user.id).all()
    favorite_styles = db.query(UserStyle).filter(UserStyle.user_id == current_user.id).all()
    
    return EnhancedUserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        gender=current_user.gender,
        selected_size=current_user.selected_size,
        avatar_url=current_user.avatar_url,
        is_profile_complete=current_user.is_profile_complete,
        is_verified=current_user.is_verified,
        favorite_brands=[BrandResponse(
            id=ub.brand.id,
            name=ub.brand.name,
            slug=ub.brand.slug,
            logo=ub.brand.logo,
            description=ub.brand.description
        ) for ub in favorite_brands],
        favorite_styles=[StyleResponse(
            id=us.style.id,
            name=us.style.name,
            description=us.style.description,
            image=us.style.image
        ) for us in favorite_styles],
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@app.get("/api/v1/user/profile/completion-status")
async def get_profile_completion_status(current_user: User = Depends(get_current_user)):
    """Check user profile completion status"""
    missing_fields = []
    required_screens = []
    
    if not current_user.first_name:
        missing_fields.append('first_name')
    if not current_user.last_name:
        missing_fields.append('last_name')
    if not current_user.is_profile_complete:
        missing_fields.append('profile_completion')
        required_screens.append('confirmation')
    
    return {
        "isComplete": current_user.is_profile_complete,
        "missingFields": missing_fields,
        "requiredScreens": required_screens
    }

@app.get("/api/v1/user/oauth-accounts")
async def get_oauth_accounts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's OAuth accounts"""
    oauth_accounts = db.query(OAuthAccount).filter(OAuthAccount.user_id == current_user.id).all()
    
    return [
        {
            "id": account.id,
            "provider": account.provider,
            "provider_user_id": account.provider_user_id,
            "created_at": account.created_at,
            "updated_at": account.updated_at
        }
        for account in oauth_accounts
    ]

# Enhanced User Profile Management
@app.put("/api/v1/user/profile", response_model=EnhancedUserResponse)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    # Update user fields
    if profile_data.gender is not None:
        current_user.gender = profile_data.gender
    if profile_data.selected_size is not None:
        current_user.selected_size = profile_data.selected_size
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name
    
    # Update profile completion status
    current_user.is_profile_complete = bool(
        current_user.first_name and 
        current_user.last_name and 
        current_user.gender and 
        current_user.selected_size
    )
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    # Get favorite brands and styles
    favorite_brands = db.query(UserBrand).filter(UserBrand.user_id == current_user.id).all()
    favorite_styles = db.query(UserStyle).filter(UserStyle.user_id == current_user.id).all()
    
    return EnhancedUserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        gender=current_user.gender,
        selected_size=current_user.selected_size,
        avatar_url=current_user.avatar_url,
        is_profile_complete=current_user.is_profile_complete,
        is_verified=current_user.is_verified,
        favorite_brands=[BrandResponse(
            id=ub.brand.id,
            name=ub.brand.name,
            slug=ub.brand.slug,
            logo=ub.brand.logo,
            description=ub.brand.description
        ) for ub in favorite_brands],
        favorite_styles=[StyleResponse(
            id=us.style.id,
            name=us.style.name,
            description=us.style.description,
            image=us.style.image
        ) for us in favorite_styles],
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

# Brand Management
@app.get("/api/v1/brands", response_model=List[BrandResponse])
async def get_brands(db: Session = Depends(get_db)):
    """Get all available brands"""
    brands = db.query(Brand).all()
    return [
        BrandResponse(
            id=brand.id,
            name=brand.name,
            slug=brand.slug,
            logo=brand.logo,
            description=brand.description
        ) for brand in brands
    ]

@app.post("/api/v1/user/brands")
async def update_user_brands(
    brands_data: UserBrandsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's favorite brands"""
    # Remove existing brand associations
    db.query(UserBrand).filter(UserBrand.user_id == current_user.id).delete()
    
    # Add new brand associations
    for brand_id in brands_data.brand_ids:
        # Verify brand exists
        brand = db.query(Brand).filter(Brand.id == brand_id).first()
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Brand with ID {brand_id} not found"
            )
        
        user_brand = UserBrand(user_id=current_user.id, brand_id=brand_id)
        db.add(user_brand)
    
    db.commit()
    return {"message": "Favorite brands updated successfully"}

# Style Management
@app.get("/api/v1/styles", response_model=List[StyleResponse])
async def get_styles(db: Session = Depends(get_db)):
    """Get all available styles"""
    styles = db.query(Style).all()
    return [
        StyleResponse(
            id=style.id,
            name=style.name,
            description=style.description,
            image=style.image
        ) for style in styles
    ]

@app.post("/api/v1/user/styles")
async def update_user_styles(
    styles_data: UserStylesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's favorite styles"""
    # Remove existing style associations
    db.query(UserStyle).filter(UserStyle.user_id == current_user.id).delete()
    
    # Add new style associations
    for style_id in styles_data.style_ids:
        # Verify style exists
        style = db.query(Style).filter(Style.id == style_id).first()
        if not style:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Style with ID {style_id} not found"
            )
        
        user_style = UserStyle(user_id=current_user.id, style_id=style_id)
        db.add(user_style)
    
    db.commit()
    return {"message": "Favorite styles updated successfully"}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "database": "postgresql",
        "oauth_providers": [
            "google" if settings.GOOGLE_CLIENT_ID else None,
            "facebook" if settings.FACEBOOK_CLIENT_ID else None,
            "github" if settings.GITHUB_CLIENT_ID else None,
            "apple" if settings.APPLE_CLIENT_ID else None
        ]
    }

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 