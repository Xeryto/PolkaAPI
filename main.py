from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, validator, ValidationError
from typing import Optional, List, Literal
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import re
import json

# Import our modules
from config import settings
from database import get_db, init_db
from models import User, OAuthAccount, Brand, Style, UserBrand, UserStyle, Gender, FriendRequest, Friendship, FriendRequestStatus, Product, UserLikedProduct, Category, Order, OrderItem, OrderStatus
from auth_service import auth_service
from oauth_service import oauth_service
import payment_service
import schemas

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
    avatar_url: Optional[str] = None
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

class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

class UserBrandsUpdate(BaseModel):
    brand_ids: List[int]

class UserStylesUpdate(BaseModel):
    style_ids: List[str]

class EnhancedUserResponse(BaseModel):
    id: str
    username: str
    email: str
    gender: Optional[Gender] = None
    selected_size: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: bool = False
    favorite_brands: List[BrandResponse] = []
    favorite_styles: List[StyleResponse] = []
    created_at: datetime
    updated_at: datetime

# Friend System Models
class FriendRequestCreate(BaseModel):
    recipient_identifier: str  # username or email

class FriendRequestResponse(BaseModel):
    id: str
    recipient: dict  # { "id": "user_id", "username": "recipient_username" }
    status: str

class ReceivedFriendRequestResponse(BaseModel):
    id: str
    sender: dict  # { "id": "user_id", "username": "sender_username" }
    status: str

class FriendResponse(BaseModel):
    id: str
    username: str

class UserSearchResponse(BaseModel):
    id: str
    username: str
    email: str
    friend_status: Optional[str] = None # 'friend', 'request_received', 'request_sent', 'not_friend'

class PublicUserProfileResponse(BaseModel):
    id: str
    username: str
    gender: Optional[Gender] = None

class MessageResponse(BaseModel):
    message: str

class ProductResponse(BaseModel):
    id: str
    name: str
    price: str
    image_url: Optional[str] = None
    available_sizes: Optional[List[str]] = None
    is_liked: Optional[bool] = None # Only for /for_user endpoint

class ToggleFavoriteRequest(BaseModel):
    product_id: str
    action: Literal["like", "unlike"]

class PaymentCreateResponse(BaseModel):
    confirmation_url: str

class PaymentStatusResponse(BaseModel):
    status: str

@app.get("/api/v1/payments/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """Get the status of a payment by its ID and update it from YooKassa"""
    order = db.query(Order).filter(Order.id == payment_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Fetch real-time status from YooKassa
    yookassa_status = payment_service.get_yookassa_payment_status(order.id)
    if yookassa_status:
        # Update local order status if different
        if order.status.value.lower() != yookassa_status.lower():
            print(f"Updating order {order.id} status from {order.status.value} to {yookassa_status} based on YooKassa.")
            order.status = OrderStatus(yookassa_status.upper()) # Assuming YooKassa status matches OrderStatus enum
            db.commit()
            db.refresh(order)
    else:
        print(f"Could not fetch real-time status for order {order.id} from YooKassa.")

    return PaymentStatusResponse(status=order.status.value)

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
        password_hash=password_hash
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
            avatar_url=user.avatar_url,
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
            avatar_url=user.avatar_url,
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
        gender=current_user.gender,
        selected_size=current_user.selected_size,
        avatar_url=current_user.avatar_url,
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
async def get_profile_completion_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check user profile completion status"""
    missing_fields = []
    required_screens = []
    
    is_gender_complete = current_user.gender is not None
    is_brands_complete = db.query(UserBrand).filter(UserBrand.user_id == current_user.id).count() > 0
    is_styles_complete = db.query(UserStyle).filter(UserStyle.user_id == current_user.id).count() > 0
    
    is_complete = is_gender_complete and is_brands_complete and is_styles_complete
    
    if not is_gender_complete:
        missing_fields.append('gender')
        required_screens.append('gender_selection') # Assuming a screen for gender selection
    if not is_brands_complete:
        missing_fields.append('favorite_brands')
        required_screens.append('brand_selection') # Assuming a screen for brand selection
    if not is_styles_complete:
        missing_fields.append('favorite_styles')
        required_screens.append('style_selection') # Assuming a screen for style selection
    
    return {
        "isComplete": is_complete,
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
    
    # Update profile completion status
    # The is_profile_complete status is now determined by the /api/v1/user/profile/completion-status endpoint
    # and is based on gender, favorite brands, and favorite styles.
    # This field is no longer directly updated here.
    
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
        gender=current_user.gender,
        selected_size=current_user.selected_size,
        avatar_url=current_user.avatar_url,
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

@app.get("/api/v1/categories", response_model=List[CategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """Get all available categories"""
    categories = db.query(Category).all()
    return [
        CategoryResponse(
            id=category.id,
            name=category.name,
            description=category.description
        ) for category in categories
    ]

# Liking Items Endpoint
@app.post("/api/v1/user/favorites/toggle", response_model=MessageResponse)
async def toggle_favorite_item(
    toggle_data: ToggleFavoriteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add or remove an item from the user's favorites (liked items)"""
    product_id = toggle_data.product_id
    action = toggle_data.action

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    existing_like = db.query(UserLikedProduct).filter(
        UserLikedProduct.user_id == current_user.id,
        UserLikedProduct.product_id == product_id
    ).first()

    if action == "like":
        if existing_like:
            return {"message": "Item already liked."}
        else:
            user_liked_product = UserLikedProduct(
                user_id=current_user.id,
                product_id=product_id
            )
            db.add(user_liked_product)
            db.commit()
            return {"message": "Item liked successfully."}
    elif action == "unlike":
        if existing_like:
            db.delete(existing_like)
            db.commit()
            return {"message": "Item unliked successfully."}
        else:
            return {"message": "Item is not liked."}

# Get User Favorites Endpoint
@app.get("/api/v1/user/favorites", response_model=List[ProductResponse])
async def get_user_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all products liked by the current user"""
    liked_products = db.query(Product).join(UserLikedProduct).filter(
        UserLikedProduct.user_id == current_user.id
    ).all()

    results = []
    for product in liked_products:
        results.append(ProductResponse(
            id=product.id,
            name=product.name,
            price=product.price,
            image_url=product.image_url,
            available_sizes=product.available_sizes.split(',') if product.available_sizes else None,
            is_liked=True # All products returned here are liked by definition
        ))
    return results

# Item Recommendations Endpoints
@app.get("/api/v1/recommendations/for_user", response_model=List[ProductResponse])
async def get_recommendations_for_user(
    limit: int = 5, # Default to 5 products
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Provide recommended items for the current user"""
    # This is a placeholder for a real recommendation engine.
    # For now, return a few random products and mark if liked by the user
    all_products = db.query(Product).order_by(func.random()).limit(limit).all() # Get random products
    liked_product_ids = {ulp.product_id for ulp in current_user.liked_products}

    recommendations = []
    for product in all_products:
        recommendations.append(ProductResponse(
            id=product.id,
            name=product.name,
            price=product.price,
            image_url=product.image_url,
            available_sizes=product.available_sizes.split(',') if product.available_sizes else None,
            is_liked=product.id in liked_product_ids
        ))
    return recommendations

@app.get("/api/v1/recommendations/for_friend/{friend_id}", response_model=List[ProductResponse])
async def get_recommendations_for_friend(
    friend_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Provide recommended items for a specific friend"""
    # # Verify friendship (optional, but good practice for privacy)
    # friendship_exists = db.query(Friendship).filter(
    #     ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id)) |
    #     ((Friendship.user_id == friend_id) & (Friendship.friend_id == current_user.id))
    # ).first()

    # if not friendship_exists:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You are not friends with this user."
    #     )

    friend_user = db.query(User).filter(User.id == friend_id).first()
    if not friend_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend not found."
        )

    # This is a placeholder for a real recommendation engine for a friend.
    # Logic would be similar to for_user, but based on friend_user's profile and interactions.
    # For now, return exactly 8 random products (without is_liked for friend's view)
    all_products = db.query(Product).order_by(func.random()).limit(8).all() # Get 8 random products
    liked_product_ids = {ulp.product_id for ulp in current_user.liked_products}

    recommendations = []
    for product in all_products:
        recommendations.append(ProductResponse(
            id=product.id,
            name=product.name,
            price=product.price,
            image_url=product.image_url,
            available_sizes=product.available_sizes.split(',') if product.available_sizes else None,
            is_liked=product.id in liked_product_ids
        ))
    return recommendations

@app.get("/api/v1/products/search", response_model=List[ProductResponse])
async def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    style: Optional[str] = None,
    limit: int = 4,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for products based on query and filters"""
    products_query = db.query(Product)

    # Apply search query
    if query:
        search_pattern = f"%{query.lower()}%"
        products_query = products_query.filter(
            (Product.name.ilike(search_pattern)) |
            (Product.description.ilike(search_pattern))
        )

    # Apply filters
    if category and category != "Категория":
        products_query = products_query.filter(Product.category_id == category)

    if brand and brand != "Бренд":
        products_query = products_query.join(Brand).filter(Brand.name.ilike(f"%{brand.lower()}%"))

    if style and style != "Стиль":
        products_query = products_query.join(Product.styles).join(Style).filter(Style.name.ilike(f"%{style.lower()}%"))

    # Apply pagination
    products_query = products_query.offset(offset).limit(limit)

    products = products_query.all()
    liked_product_ids = {ulp.product_id for ulp in current_user.liked_products}

    results = []
    for product in products:
        results.append(ProductResponse(
            id=product.id,
            name=product.name,
            price=product.price,
            image_url=product.image_url,
            available_sizes=product.available_sizes.split(',') if product.available_sizes else None,
            is_liked=product.id in liked_product_ids
        ))
    return results

# Friend System Endpoints
@app.post("/api/v1/friends/request", response_model=MessageResponse)
async def send_friend_request(
    request_data: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a friend request to another user"""
    # Find recipient by username or email
    recipient = None
    if '@' in request_data.recipient_identifier:
        recipient = db.query(User).filter(User.email == request_data.recipient_identifier).first()
    else:
        recipient = db.query(User).filter(User.username == request_data.recipient_identifier).first()
    
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    if recipient.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send friend request to yourself"
        )
    
    # Check if already friends
    existing_friendship = db.query(Friendship).filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == recipient.id)) |
        ((Friendship.user_id == recipient.id) & (Friendship.friend_id == current_user.id))
    ).first()
    
    if existing_friendship:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already friends"
        )
    
    # Check if friend request already exists
    existing_request = db.query(FriendRequest).filter(
        ((FriendRequest.sender_id == current_user.id) & (FriendRequest.recipient_id == recipient.id)) |
        ((FriendRequest.sender_id == recipient.id) & (FriendRequest.recipient_id == current_user.id))
    ).first()
    
    if existing_request:
        if existing_request.status == FriendRequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Friend request already pending"
            )
    
    # Create new friend request
    friend_request = FriendRequest(
        sender_id=current_user.id,
        recipient_id=recipient.id,
        status=FriendRequestStatus.PENDING
    )
    
    db.add(friend_request)
    db.commit()
    
    return {"message": "Friend request sent."}

@app.get("/api/v1/friends/requests/sent", response_model=List[FriendRequestResponse])
async def get_sent_friend_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sent friend requests"""
    requests = db.query(FriendRequest).filter(
        FriendRequest.sender_id == current_user.id
    ).all()
    
    return [
        {
            "id": req.id,
            "recipient": {
                "id": req.recipient.id,
                "username": req.recipient.username
            },
            "status": req.status
        }
        for req in requests
    ]

@app.get("/api/v1/friends/requests/received", response_model=List[ReceivedFriendRequestResponse])
async def get_received_friend_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get received friend requests"""
    requests = db.query(FriendRequest).filter(
        FriendRequest.recipient_id == current_user.id,
        FriendRequest.status == FriendRequestStatus.PENDING
    ).all()
    
    return [
        {
            "id": req.id,
            "sender": {
                "id": req.sender.id,
                "username": req.sender.username
            },
            "status": req.status
        }
        for req in requests
    ]

@app.post("/api/v1/friends/requests/{request_id}/accept", response_model=MessageResponse)
async def accept_friend_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a friend request"""
    friend_request = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.recipient_id == current_user.id,
        FriendRequest.status == FriendRequestStatus.PENDING
    ).first()
    
    if not friend_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found or not pending"
        )
    
    # Update request status
    friend_request.status = FriendRequestStatus.ACCEPTED
    friend_request.updated_at = datetime.utcnow()
    
    # Create friendship
    friendship = Friendship(
        user_id=friend_request.sender_id,
        friend_id=friend_request.recipient_id
    )
    
    db.add(friendship)
    db.delete(friend_request) # Delete the friend request after acceptance
    db.commit()
    
    return {"message": "Friend request accepted."}

@app.post("/api/v1/friends/requests/{request_id}/reject", response_model=MessageResponse)
async def reject_friend_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject a friend request"""
    friend_request = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.recipient_id == current_user.id,
        FriendRequest.status == FriendRequestStatus.PENDING
    ).first()
    
    if not friend_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found or not pending"
        )
    
    friend_request.status = FriendRequestStatus.REJECTED
    friend_request.updated_at = datetime.utcnow()
    db.delete(friend_request) # Delete the friend request after rejection
    db.commit()
    
    return {"message": "Friend request rejected."}

@app.delete("/api/v1/friends/requests/{request_id}/cancel", response_model=MessageResponse)
async def cancel_friend_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a sent friend request"""
    friend_request = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.sender_id == current_user.id,
        FriendRequest.status == FriendRequestStatus.PENDING
    ).first()
    
    if not friend_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found or not pending"
        )
    
    friend_request.status = FriendRequestStatus.CANCELLED
    friend_request.updated_at = datetime.utcnow()
    db.delete(friend_request) # Delete the friend request after cancellation
    db.commit()
    
    return {"message": "Friend request cancelled."}

@app.get("/api/v1/friends", response_model=List[FriendResponse])
async def get_friends_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's friends list"""
    # Get friendships where current user is either user or friend
    friendships = db.query(Friendship).filter(
        (Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)
    ).all()
    
    friends = []
    for friendship in friendships:
        if friendship.user_id == current_user.id:
            friend_user = db.query(User).filter(User.id == friendship.friend_id).first()
        else:
            friend_user = db.query(User).filter(User.id == friendship.user_id).first()
        
        if friend_user:
            friends.append({
                "id": friend_user.id,
                "username": friend_user.username
            })
    
    return friends

@app.delete("/api/v1/friends/{friend_id}", response_model=MessageResponse)
async def remove_friend(
    friend_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a friend"""
    # Find the friendship entry
    friendship = db.query(Friendship).filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id)) |
        ((Friendship.user_id == friend_id) & (Friendship.friend_id == current_user.id))
    ).first()

    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friendship not found"
        )

    db.delete(friendship)
    db.commit()

    return {"message": "Friend removed successfully"}

@app.get("/api/v1/users/search", response_model=List[UserSearchResponse])
async def search_users(
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for users by username or email"""
    if len(query) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters"
        )
    
    # Search by username or email (case insensitive)
    users = db.query(User).filter(
        (User.username.ilike(f"%{query}%") | User.email.ilike(f"%{query}%")) &
        (User.id != current_user.id)  # Exclude current user
    ).limit(20).all()
    
    result = []
    for user in users:
        friend_status = 'not_friend'
        
        # Check if already friends
        existing_friendship = db.query(Friendship).filter(
            ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user.id)) |
            ((Friendship.user_id == user.id) & (Friendship.friend_id == current_user.id))
        ).first()
        
        if existing_friendship:
            friend_status = 'friend'
        else:
            # Check for pending friend requests
            sent_request = db.query(FriendRequest).filter(
                FriendRequest.sender_id == current_user.id,
                FriendRequest.recipient_id == user.id,
                FriendRequest.status == FriendRequestStatus.PENDING
            ).first()
            
            received_request = db.query(FriendRequest).filter(
                FriendRequest.sender_id == user.id,
                FriendRequest.recipient_id == current_user.id,
                FriendRequest.status == FriendRequestStatus.PENDING
            ).first()
            
            if sent_request:
                friend_status = 'request_sent'
            elif received_request:
                friend_status = 'request_received'
        
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "friend_status": friend_status
        })
    
    return result

@app.get("/api/v1/users/{user_id}/profile", response_model=PublicUserProfileResponse)
async def get_public_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get public profile of another user"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "gender": user.gender
    }

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

@app.post("/api/v1/payments/create", response_model=PaymentCreateResponse)
async def create_payment_endpoint(
    payment_data: schemas.PaymentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print("Entered create_payment_endpoint")
    print(f"Request headers: {request.headers}")
    try:
        raw_request_body = await request.body()
        print(f"Raw incoming request body for /api/v1/payments/create: {raw_request_body.decode()}")

        # This line is where Pydantic validation happens implicitly
        # payment_data = schemas.PaymentCreate.parse_raw(raw_request_body) # This is handled by FastAPI automatically

        confirmation_url = payment_service.create_payment(
            db=db,
            user_id=current_user.id,
            amount=float(payment_data.amount.value),
            currency=payment_data.amount.currency,
            description=payment_data.description,
            return_url=payment_data.returnUrl,
            items=payment_data.items
        )
        #print(f"Receipt data sent to payment_service: {payment_data.receipt.dict() if payment_data.receipt else None}")
        return PaymentCreateResponse(confirmation_url=confirmation_url)
    except ValidationError as e:
        print(f"Pydantic Validation Error: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/v1/orders", response_model=List[schemas.OrderResponse])
async def get_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all orders for the current user"""
    orders = db.query(Order).filter(Order.user_id == current_user.id).all()
    
    response = []
    for order in orders:
        order_items = []
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                order_items.append(schemas.OrderItemResponse(
                    id=product.id,
                    name=product.name,
                    price=item.price,
                    size=item.size,
                    image=product.image_url,
                    delivery=schemas.Delivery(
                        cost="350 р",
                        estimatedTime="1-3 дня",
                        tracking_number=None
                    )
                ))

        response.append(schemas.OrderResponse(
            id=order.id,
            number=order.order_number,
            total=f"{order.total_amount} {order.currency}",
            date=order.created_at,
            status=order.status.value,
            items=order_items
        ))
    return response


@app.post("/api/v1/payments/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle YooKassa payment webhooks"""
    if not payment_service.verify_webhook_ip(request.client.host):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid IP address"
        )

    request_body = await request.body()
    payload = json.loads(request_body)
    print(f"Webhook payload received: {payload}")
    event = payload.get("event")
    print(f"Webhook event: {event}")
    if event == "payment.succeeded":
        payment = payload.get("object", {})
        order_id = payment.get("metadata", {}).get("order_id")
        print(f"Payment succeeded - Order ID: {order_id}")
        if order_id:
            payment_service.update_order_status(db, order_id, OrderStatus.PAID)
    elif event == "payment.canceled":
        payment = payload.get("object", {})
        order_id = payment.get("metadata", {}).get("order_id")
        print(f"Payment canceled - Order ID: {order_id}")
        if order_id:
            payment_service.update_order_status(db, order_id, OrderStatus.CANCELED)
    db.commit() # Added commit here
    return {"status": "ok"}


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
