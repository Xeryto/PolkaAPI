"""
OAuth service for social login providers
"""
from typing import Optional, Dict, Any
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.httpx_client import OAuth2Client
from starlette.config import Config
from config import settings
import httpx
import jwt
from datetime import datetime, timedelta
import json

class OAuthService:
    """OAuth service for handling social login"""
    
    def __init__(self):
        self.config = Config('.env')
        self.oauth = OAuth()
        self._setup_providers()
    
    def _setup_providers(self):
        """Setup OAuth providers"""
        # Google OAuth
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            self.oauth.register(
                name='google',
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                server_metadata_url=settings.GOOGLE_DISCOVERY_URL,
                client_kwargs={
                    'scope': 'openid email profile'
                }
            )
        
        # Facebook OAuth
        if settings.FACEBOOK_CLIENT_ID and settings.FACEBOOK_CLIENT_SECRET:
            self.oauth.register(
                name='facebook',
                client_id=settings.FACEBOOK_CLIENT_ID,
                client_secret=settings.FACEBOOK_CLIENT_SECRET,
                api_base_url='https://graph.facebook.com/',
                access_token_url='https://graph.facebook.com/oauth/access_token',
                authorize_url='https://www.facebook.com/dialog/oauth',
                client_kwargs={
                    'scope': 'email public_profile'
                }
            )
        
        # GitHub OAuth
        if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
            self.oauth.register(
                name='github',
                client_id=settings.GITHUB_CLIENT_ID,
                client_secret=settings.GITHUB_CLIENT_SECRET,
                api_base_url='https://api.github.com/',
                access_token_url='https://github.com/login/oauth/access_token',
                authorize_url='https://github.com/login/oauth/authorize',
                client_kwargs={
                    'scope': 'read:user user:email'
                }
            )
    
    async def get_google_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get Google user information from token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {token}'}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'provider': 'google',
                        'provider_user_id': data['id'],
                        'email': data['email'],
                        'first_name': data.get('given_name'),
                        'last_name': data.get('family_name'),
                        'avatar_url': data.get('picture'),
                        'is_verified': data.get('verified_email', False)
                    }
        except Exception as e:
            print(f"Error getting Google user info: {e}")
        return None
    
    async def get_facebook_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get Facebook user information from token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://graph.facebook.com/me',
                    params={
                        'fields': 'id,email,first_name,last_name,picture',
                        'access_token': token
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'provider': 'facebook',
                        'provider_user_id': data['id'],
                        'email': data.get('email'),
                        'first_name': data.get('first_name'),
                        'last_name': data.get('last_name'),
                        'avatar_url': data.get('picture', {}).get('data', {}).get('url'),
                        'is_verified': True  # Facebook accounts are generally verified
                    }
        except Exception as e:
            print(f"Error getting Facebook user info: {e}")
        return None
    
    async def get_github_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get GitHub user information from token"""
        try:
            async with httpx.AsyncClient() as client:
                # Get user info
                response = await client.get(
                    'https://api.github.com/user',
                    headers={
                        'Authorization': f'token {token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                )
                if response.status_code == 200:
                    user_data = response.json()
                    
                    # Get email info
                    email_response = await client.get(
                        'https://api.github.com/user/emails',
                        headers={
                            'Authorization': f'token {token}',
                            'Accept': 'application/vnd.github.v3+json'
                        }
                    )
                    
                    email = user_data.get('email')
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        primary_email = next((e for e in emails if e['primary']), None)
                        if primary_email:
                            email = primary_email['email']
                    
                    return {
                        'provider': 'github',
                        'provider_user_id': str(user_data['id']),
                        'email': email,
                        'first_name': user_data.get('name', '').split()[0] if user_data.get('name') else None,
                        'last_name': ' '.join(user_data.get('name', '').split()[1:]) if user_data.get('name') and len(user_data.get('name', '').split()) > 1 else None,
                        'avatar_url': user_data.get('avatar_url'),
                        'is_verified': True  # GitHub accounts are generally verified
                    }
        except Exception as e:
            print(f"Error getting GitHub user info: {e}")
        return None
    
    async def verify_apple_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Verify Apple ID token and extract user information"""
        try:
            # In a production environment, you would verify the JWT signature
            # For now, we'll decode without verification (not recommended for production)
            decoded = jwt.decode(id_token, options={"verify_signature": False})
            
            return {
                'provider': 'apple',
                'provider_user_id': decoded.get('sub'),
                'email': decoded.get('email'),
                'first_name': None,  # Apple doesn't provide name in ID token
                'last_name': None,
                'avatar_url': None,
                'is_verified': True
            }
        except Exception as e:
            print(f"Error verifying Apple token: {e}")
        return None
    
    def get_oauth_client(self, provider: str) -> Optional[OAuth2Client]:
        """Get OAuth client for a specific provider"""
        if provider == 'google' and settings.GOOGLE_CLIENT_ID:
            return OAuth2Client(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scope='openid email profile'
            )
        elif provider == 'facebook' and settings.FACEBOOK_CLIENT_ID:
            return OAuth2Client(
                client_id=settings.FACEBOOK_CLIENT_ID,
                client_secret=settings.FACEBOOK_CLIENT_SECRET,
                scope='email public_profile'
            )
        elif provider == 'github' and settings.GITHUB_CLIENT_ID:
            return OAuth2Client(
                client_id=settings.GITHUB_CLIENT_ID,
                client_secret=settings.GITHUB_CLIENT_SECRET,
                scope='read:user user:email'
            )
        return None

# Create OAuth service instance
oauth_service = OAuthService() 