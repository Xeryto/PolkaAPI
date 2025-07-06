# PolkaAPI - Modern Authentication Backend

A production-ready, scalable authentication API built with **FastAPI** and **PostgreSQL**, featuring comprehensive user management, OAuth social login integration, and fashion-focused user preferences.

## 🚀 **Key Features**

### **Authentication & Security**

- **JWT-based authentication** with configurable token expiration
- **Password hashing** using bcrypt with salt
- **OAuth 2.0 integration** for Google, Facebook, GitHub, and Apple
- **Flexible login** - users can authenticate with email OR username
- **Input validation** with Pydantic models and comprehensive error handling

### **User Management**

- **Complete user profiles** with gender, size preferences, and personal information
- **Favorite brands & styles** with many-to-many relationships
- **Profile completion tracking** with missing field detection
- **OAuth account linking** - users can connect multiple social accounts

### **Database & Architecture**

- **PostgreSQL** with SQLAlchemy ORM for robust data management
- **Alembic migrations** for version-controlled schema changes
- **Proper indexing** on frequently queried fields
- **Cascade deletes** and referential integrity
- **Connection pooling** for optimal performance

### **API Design**

- **RESTful endpoints** following best practices
- **Comprehensive error handling** with proper HTTP status codes
- **Request/response validation** with Pydantic models
- **Auto-generated API documentation** (Swagger UI & ReDoc)
- **CORS support** for cross-origin requests

## 🛠 **Technology Stack**

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL 15 with SQLAlchemy 2.0.23
- **Authentication**: JWT, bcrypt, OAuth 2.0
- **Migrations**: Alembic 1.12.1
- **Validation**: Pydantic 2.5.0
- **HTTP Client**: httpx 0.25.2
- **OAuth**: Authlib 1.2.1

## 📊 **Database Schema**

```sql
-- Core user management
users (id, username, email, password_hash, first_name, last_name,
       gender, selected_size, avatar_url, is_profile_complete,
       is_verified, created_at, updated_at)

-- OAuth integration
oauth_accounts (id, user_id, provider, provider_user_id,
                access_token, refresh_token, expires_at)

-- Fashion preferences
brands (id, name, slug, logo, description)
styles (id, name, description, image)
user_brands (user_id, brand_id) -- Many-to-many
user_styles (user_id, style_id) -- Many-to-many
```

## 🔧 **Quick Start**

### **Prerequisites**

- Python 3.8+
- PostgreSQL 12+
- pip

### **Installation**

```bash
# Clone repository
git clone <repository-url>
cd PolkaAPI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install

# Set up environment variables
export SECRET_KEY="your-super-secret-key"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/polkaDB"

# Initialize database
make db-init

# Start development server
make run
```

### **Available Commands**

```bash
make help          # Show all available commands
make install       # Install dependencies
make run           # Start development server
make run-dev       # Start with auto-reload
make test          # Run API tests
make format        # Format code with black & isort
make lint          # Run linting checks
make db-init       # Initialize database with sample data
make db-migrate    # Apply pending migrations
make docs          # Open API documentation
```

## 📚 **API Documentation**

Once running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### **Core Endpoints**

| Method | Endpoint                   | Description            |
| ------ | -------------------------- | ---------------------- |
| `POST` | `/api/v1/auth/register`    | User registration      |
| `POST` | `/api/v1/auth/login`       | Login (email/username) |
| `POST` | `/api/v1/auth/oauth/login` | OAuth login            |
| `GET`  | `/api/v1/user/profile`     | Get user profile       |
| `PUT`  | `/api/v1/user/profile`     | Update user profile    |
| `GET`  | `/api/v1/brands`           | Get available brands   |
| `POST` | `/api/v1/user/brands`      | Update favorite brands |
| `GET`  | `/api/v1/styles`           | Get available styles   |
| `POST` | `/api/v1/user/styles`      | Update favorite styles |

## 🔐 **Security Features**

- **JWT tokens** with configurable expiration
- **Password hashing** using bcrypt with salt
- **Input sanitization** and validation
- **SQL injection protection** via SQLAlchemy ORM
- **CORS configuration** for secure cross-origin requests
- **Environment-based configuration** for secrets

## 🧪 **Testing**

```bash
# Run comprehensive API tests
make test
```

The test suite covers:

- User registration and authentication
- Profile management and updates
- Brand and style preferences
- OAuth integration (mock)
- Error handling and validation
- Database operations

## 📈 **Performance & Scalability**

- **Connection pooling** for database efficiency
- **Proper indexing** on frequently queried fields
- **Lazy loading** of relationships
- **Stateless JWT authentication** for horizontal scaling
- **Efficient queries** with SQLAlchemy optimization

## 🏗 **Architecture Highlights**

### **Clean Architecture**

- **Separation of concerns** with dedicated service layers
- **Dependency injection** for testability
- **Repository pattern** for data access
- **Configuration management** with environment variables

### **Code Quality**

- **Type hints** throughout the codebase
- **Comprehensive error handling**
- **Logging and monitoring** ready
- **Code formatting** with black and isort
- **Linting** with flake8 and mypy

### **Database Design**

- **Normalized schema** with proper relationships
- **Foreign key constraints** for data integrity
- **Indexes** on performance-critical fields
- **Migration system** for schema evolution

## 🚀 **Deployment Ready**

- **Environment configuration** for different stages
- **Database migration system** for zero-downtime deployments
- **Health check endpoints** for monitoring
- **Comprehensive logging** for debugging
- **Error handling** for production scenarios

## 📝 **Development Workflow**

1. **Feature Development**: Create new Alembic migrations for schema changes
2. **Testing**: Comprehensive test suite with real API calls
3. **Code Quality**: Automated formatting and linting
4. **Documentation**: Auto-generated API docs from code
5. **Deployment**: Environment-based configuration management

## 🎯 **Business Value**

This API demonstrates:

- **Production-ready authentication** system
- **Scalable architecture** for high-traffic applications
- **Modern development practices** with proper tooling
- **Security best practices** for user data protection
- **Flexible user preference system** for personalized experiences

## 📞 **Contact**

This project showcases modern backend development practices with FastAPI, PostgreSQL, and comprehensive authentication systems. Perfect for demonstrating full-stack development capabilities and production-ready API design.

---

**Built with ❤️ using FastAPI, PostgreSQL, and modern Python practices**
