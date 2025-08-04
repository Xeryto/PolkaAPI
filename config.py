"""
Configuration settings for PolkaAPI
"""
import os
from typing import List, Optional

class Settings:
    """Application settings"""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PolkaAPI - Authentication Backend"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://polkagress_user:2SANlJyrpZMLzEbjeqfjszjxOmCzgcFm@dpg-d26oajndiees73aohlpg-a.oregon-postgres.render.com/polkagress")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React development
        "http://localhost:8080",  # Vue development
        "http://localhost:4200",  # Angular development
        "http://localhost:19006", # Expo development
        "*"  # Allow all origins in development
    ]
    
    # OAuth Configuration
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_DISCOVERY_URL: str = "https://accounts.google.com/.well-known/openid_configuration"
    
    # Facebook OAuth
    FACEBOOK_CLIENT_ID: Optional[str] = os.getenv("FACEBOOK_CLIENT_ID")
    FACEBOOK_CLIENT_SECRET: Optional[str] = os.getenv("FACEBOOK_CLIENT_SECRET")
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: Optional[str] = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
    
    # Apple OAuth
    APPLE_CLIENT_ID: Optional[str] = os.getenv("APPLE_CLIENT_ID")
    APPLE_CLIENT_SECRET: Optional[str] = os.getenv("APPLE_CLIENT_SECRET")
    APPLE_TEAM_ID: Optional[str] = os.getenv("APPLE_TEAM_ID")
    APPLE_KEY_ID: Optional[str] = os.getenv("APPLE_KEY_ID")
    APPLE_PRIVATE_KEY: Optional[str] = os.getenv("APPLE_PRIVATE_KEY")
    
    # OAuth Redirect URLs
    OAUTH_REDIRECT_URL: str = os.getenv("OAUTH_REDIRECT_URL", "http://localhost:8000/api/v1/auth/oauth/callback")
    
    # Validation Rules
    MIN_USERNAME_LENGTH: int = 3
    MIN_PASSWORD_LENGTH: int = 6
    MAX_USERNAME_LENGTH: int = 50
    MAX_EMAIL_LENGTH: int = 255
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Development
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # YooKassa
    YOOKASSA_SHOP_ID: Optional[str] = os.getenv("YOOKASSA_SHOP_ID")
    YOOKASSA_SECRET_KEY: Optional[str] = os.getenv("YOOKASSA_SECRET_KEY")

    # UniSender
    UNISENDER_API_KEY: Optional[str] = os.getenv("UNISENDER_API_KEY")
    UNISENDER_FROM_EMAIL: Optional[str] = os.getenv("UNISENDER_FROM_EMAIL")
    UNISENDER_FROM_NAME: Optional[str] = os.getenv("UNISENDER_FROM_NAME")
    UNISENDER_LIST_ID: Optional[str] = os.getenv("UNISENDER_LIST_ID")

# Create settings instance
settings = Settings() 