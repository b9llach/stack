# FastAPI Template

A production-ready FastAPI template with role-based access control, 2FA, email notifications, and real-time WebSocket support.

## Features

### Core Features
- **Async Everything**: Fully async FastAPI with PostgreSQL (asyncpg) and Redis
- **Role-Based Access Control**: User, Admin, and Superadmin roles with granular permissions
- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **Google OAuth Login**: Native Google Sign-In integration (optional)
- **Stripe Integration**: Full payment processing, subscriptions, and Connect (optional)
- **Two-Factor Authentication**: Per-user 2FA via email with customizable settings
- **Rich User Profiles**: Phone, avatar, bio, timezone, language preferences, and activity tracking
- **Email Service**: Full SMTP integration with HTML templates
- **WebSockets**: Real-time communication with room management and broadcasting
- **Rate Limiting**: Configurable IP-based rate limiting
- **Redis Caching**: Built-in caching with utilities
- **Input Validation**: Pydantic schemas for all requests/responses
- **Health Checks**: Database and cache connectivity monitoring

### Security Features
- Bcrypt password hashing
- JWT tokens with configurable expiration
- OAuth 2.0 authentication (Google)
- API key support
- CORS configuration
- SQL injection protection
- Rate limiting middleware
- Per-user 2FA support

### Developer Experience
- Auto-generated API documentation (Swagger UI + ReDoc)
- Setup scripts for SECRET_KEY and superadmin creation
- Comprehensive logging
- Generic CRUD base classes
- Type hints throughout
- Structured project layout

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL (local or cloud like Neon)
- Redis (local or cloud like Upstash)

### Installation

1. **Clone and setup virtual environment:**
```bash
git clone https://github.com/b9llach/fastapi-template.git
cd fastapi-template
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Generate SECRET_KEY:**
```bash
python setup_secret_key.py
```
This creates a secure SECRET_KEY and optionally updates your `.env` file.

4. **Configure environment variables:**
Create a `.env` file (see `.env.example` for template):
```env
# Application
PROJECT_NAME=My FastAPI App
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Database (supports SSL automatically)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=<generated-from-setup-script>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (optional, required for 2FA)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=True
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@yourdomain.com

# CORS
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# Google OAuth (optional)
GOOGLE_OAUTH_ENABLED=True
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Stripe (optional)
STRIPE_ENABLED=True
STRIPE_SECRET_KEY=sk_test_your-secret-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
```

5. **Create first superadmin:**
```bash
python setup_first_superadmin.py
```
Interactive script to create your first superadmin user.

6. **Run the application:**
```bash
python main.py
# Or: uvicorn main:app --reload
```

7. **Access the API:**
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Project Structure

```
fastapi-template/
├── main.py                              # Application entry point
├── setup_secret_key.py                  # SECRET_KEY generator
├── setup_first_superadmin.py            # Superadmin creation script
├── requirements.txt                     # Python dependencies
├── .env.example                         # Environment variables template
├── .gitignore                           # Git ignore rules
│
├── app/
│   ├── api/
│   │   ├── dependencies/
│   │   │   ├── auth.py                  # Auth dependencies (role checks)
│   │   │   └── pagination.py           # Pagination helpers
│   │   ├── middleware/
│   │   │   └── logging.py               # Request/response logging
│   │   └── routers/
│   │       ├── auth.py                  # Authentication endpoints (register, login, 2FA)
│   │       ├── health.py                # Health check endpoints
│   │       └── users.py                 # User management endpoints
│   │
│   ├── core/
│   │   ├── async_database.py            # Async SQLAlchemy setup with SSL support
│   │   ├── cache.py                     # Redis cache utilities
│   │   ├── config.py                    # Configuration management
│   │   └── security.py                  # Password hashing, JWT tokens
│   │
│   ├── db/
│   │   ├── models/
│   │   │   ├── enums.py                 # UserRole enum
│   │   │   └── user.py                  # User model
│   │   ├── schemas/
│   │   │   └── user.py                  # Pydantic schemas
│   │   └── utils/
│   │       ├── crud.py                  # Generic CRUD base class
│   │       └── user_crud.py             # User-specific CRUD operations
│   │
│   ├── middleware/
│   │   └── rate_limiting.py             # Rate limiting middleware
│   │
│   ├── services/
│   │   ├── email_service.py             # Email/SMTP service with 2FA
│   │   └── user_service.py              # User business logic
│   │
│   ├── utils/
│   │   ├── helpers.py                   # General utilities
│   │   ├── logger.py                    # Logging configuration
│   │   └── validators.py                # Custom validators
│   │
│   └── websockets/
│       ├── connection_manager.py        # WebSocket connection management
│       └── router.py                    # WebSocket endpoints
│
└── docs/
    ├── ROLES.md                         # Role-based access control guide
    ├── EMAIL_SETUP.md                   # Email/SMTP configuration guide
    └── USER_SETTINGS.md                 # User settings and 2FA guide
```

## API Endpoints

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/register` | Register new user | No |
| POST | `/login` | Login (username or email) | No |
| GET | `/google/login` | Initiate Google OAuth login | No |
| GET | `/google/callback` | Google OAuth callback (returns JWT) | No |
| POST | `/verify-2fa` | Verify 2FA code | No |
| POST | `/enable-2fa` | Enable 2FA for current user | Yes |
| POST | `/disable-2fa` | Disable 2FA | Yes |
| POST | `/test-2fa` | Test 2FA email | Yes |

### Users (`/api/v1/users`)
| Method | Endpoint | Description | Auth Required | Role Required |
|--------|----------|-------------|---------------|---------------|
| GET | `/me` | Get current user info | Yes | Any |
| GET | `/` | List all users | Yes | Admin |
| GET | `/role/{role}` | List users by role | Yes | Admin |
| GET | `/get/{user_id}` | Get user by ID | Yes | Self or Admin |
| PUT | `/update/{user_id}` | Update user | Yes | Self or Admin |
| PUT | `/update/{user_id}/role` | Update user role | Yes | Superadmin |
| DELETE | `/delete/{user_id}` | Delete user | Yes | Admin |

### Health (`/api/v1/health`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Basic health check |
| GET | `/db` | Database connectivity |
| GET | `/cache` | Redis cache connectivity |

### Stripe (`/api/v1/stripe`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/customers` | Create Stripe customer | Yes |
| GET | `/customers/me` | Get current user's customer info | Yes |
| POST | `/payment-intents` | Create payment intent | Yes |
| POST | `/payment-methods/attach` | Attach payment method to customer | Yes |
| GET | `/payment-methods` | List payment methods | Yes |
| POST | `/subscriptions` | Create subscription | Yes |
| POST | `/subscriptions/{id}/cancel` | Cancel subscription | Yes |
| POST | `/connect/accounts` | Create Connect account | Yes |
| POST | `/connect/account-links` | Create Connect onboarding link | Yes |
| GET | `/connect/accounts/me` | Get Connect account info | Yes |
| POST | `/webhooks` | Handle Stripe webhooks | No |
| GET | `/config` | Get publishable key | Yes |

### WebSockets
| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/ws/{client_id}` | General WebSocket |
| `ws://localhost:8000/ws/chat/{room_id}?client_id={id}` | Chat room |

## Usage Examples

### Registration
```bash
# Basic registration (minimal fields)
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "securepass123"
  }'

# Registration with optional profile fields
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "bio": "Software developer and FastAPI enthusiast",
    "timezone": "America/New_York",
    "password": "securepass123",
    "role": "user"
  }'
```

### Login (Username or Email)
```bash
# Login with username
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "johndoe",
    "password": "securepass123"
  }'

# Login with email
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "john@example.com",
    "password": "securepass123"
  }'
```

### Google OAuth Login
```bash
# In a browser, visit:
http://localhost:8000/api/v1/auth/google/login

# This will:
# 1. Redirect to Google's OAuth consent screen
# 2. User authorizes the app
# 3. Redirect to callback endpoint
# 4. Return JWT tokens (access_token, refresh_token)
```

Or use in a frontend:
```javascript
// Redirect user to Google login
window.location.href = 'http://localhost:8000/api/v1/auth/google/login';

// Handle the callback (tokens will be returned)
// You can then store the access_token for API requests
```

### Using JWT Token
```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/myclient');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Message:', data);
};

// Join a room
ws.send(JSON.stringify({
    type: 'join_room',
    room: 'lobby'
}));

// Send message to room
ws.send(JSON.stringify({
    type: 'room_message',
    room: 'lobby',
    content: 'Hello everyone!'
}));
```

## Role-Based Access Control

The system has three roles with hierarchical permissions:

### User (Default)
- View and edit own profile
- Access basic endpoints
- Enable/disable 2FA for self

### Admin
- All User permissions
- View all users
- Manage users (create, update, delete)
- Cannot change user roles

### Superadmin
- All Admin permissions
- Change user roles
- Full system access

**Example: Role-specific endpoint**
```python
from app.api.dependencies.auth import get_current_admin_user

@router.get("/admin-only")
async def admin_endpoint(
    current_user: User = Depends(get_current_admin_user)
):
    # Only admin or superadmin can access
    return {"message": "Admin access granted"}
```

See [ROLES.md](ROLES.md) for complete documentation.

## User Model

The User model includes comprehensive profile and tracking fields:

### Core Identity
- `username` - Unique username (3-50 chars)
- `email` - Unique email address
- `first_name` - User's first name (optional)
- `last_name` - User's last name (optional)
- `password` - Securely hashed with bcrypt

### Contact & Profile
- `phone_number` - Phone number (optional, up to 20 chars)
- `phone_verified` - Phone verification status (default: False)
- `avatar_url` - Profile picture URL (optional, up to 500 chars)
- `bio` - User bio/description (optional, text field)

### Settings & Preferences
- `timezone` - User's timezone (default: "UTC")
- `language` - Language preference (default: "en")

### Security & Status
- `role` - User role (USER, ADMIN, SUPERADMIN)
- `is_active` - Account active status
- `two_fa_enabled` - 2FA enabled for this user
- `email_verified` - Email verification status

### Timestamps
- `last_login_at` - Last successful login timestamp
- `created_at` - Account creation timestamp
- `updated_at` - Last update timestamp

**All profile fields are optional during registration** - users only need username, email, and password to get started. Additional fields can be updated later via the `/users/update/{user_id}` endpoint.

## Two-Factor Authentication (2FA)

2FA is **per-user**, not global. Each user can enable/disable it independently.

### Enable 2FA
```bash
curl -X POST "http://localhost:8000/api/v1/auth/enable-2fa" \
  -H "Authorization: Bearer <token>"
```

### Login with 2FA
1. Login normally - system detects 2FA is enabled
2. Receive 6-digit code via email
3. Submit code to `/verify-2fa` endpoint
4. Receive JWT tokens

See [USER_SETTINGS.md](USER_SETTINGS.md) for complete guide.

## Email Configuration

### Gmail Setup
1. Enable 2-Step Verification
2. Generate App Password
3. Configure `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=True
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
```

### Testing Email
```bash
curl -X POST "http://localhost:8000/api/v1/auth/test-2fa" \
  -H "Authorization: Bearer <token>"
```

See [EMAIL_SETUP.md](EMAIL_SETUP.md) for other providers (Outlook, SendGrid, AWS SES).

## Google OAuth Configuration

To enable Google OAuth login:

### 1. Create Google OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project (or select existing)
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Configure OAuth consent screen if prompted
6. Choose "Web application" as application type
7. Add authorized redirect URIs:
   - `http://localhost:8000/api/v1/auth/google/callback` (development)
   - `https://yourdomain.com/api/v1/auth/google/callback` (production)
8. Copy your Client ID and Client Secret

### 2. Configure Environment Variables
```env
GOOGLE_OAUTH_ENABLED=True
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

### 3. How It Works
- OAuth users don't need passwords (stored as `NULL` in database)
- If user registers with password first, then logs in with Google using same email, OAuth is linked to existing account
- Users get their profile picture from Google automatically (`avatar_url`)
- Email is automatically verified for Google OAuth users

## Stripe Configuration

To enable Stripe payments and subscriptions:

### 1. Create Stripe Account
1. Sign up at [Stripe Dashboard](https://dashboard.stripe.com/register)
2. Complete account setup
3. Get API keys from [API Keys page](https://dashboard.stripe.com/apikeys)

### 2. Configure Environment Variables
```env
STRIPE_ENABLED=True
STRIPE_SECRET_KEY=sk_test_your-secret-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
STRIPE_CURRENCY=usd
```

### 3. Set Up Webhooks
1. Go to [Webhooks Dashboard](https://dashboard.stripe.com/webhooks)
2. Add endpoint: `https://yourdomain.com/api/v1/stripe/webhooks`
3. Select events to listen for:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `account.updated` (for Connect)
4. Copy webhook signing secret to `STRIPE_WEBHOOK_SECRET`

### 4. Features Available

**Payments:**
- Create customers automatically for users
- Process one-time payments via Payment Intents
- Save and manage payment methods
- Support for multiple currencies

**Subscriptions:**
- Create and manage recurring subscriptions
- Cancel subscriptions (immediate or at period end)
- Automatic invoice creation

**Stripe Connect:**
- Onboard sellers/service providers
- Create Connect accounts (Express, Standard, Custom)
- Process platform payments with splits
- Transfer funds to connected accounts

### 5. Usage Examples

**Create a Payment Intent:**
```bash
curl -X POST "http://localhost:8000/api/v1/stripe/payment-intents" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 2000,
    "currency": "usd",
    "description": "Product purchase"
  }'
```

**Create a Subscription:**
```bash
curl -X POST "http://localhost:8000/api/v1/stripe/subscriptions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "price_id": "price_xxxxxxxxxxxxx"
  }'
```

**Create Connect Account:**
```bash
curl -X POST "http://localhost:8000/api/v1/stripe/connect/accounts" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "country": "US",
    "account_type": "express"
  }'
```

## Database Migrations

### Using Alembic (Production)
```bash
# Initialize Alembic
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Auto-creation (Development)
The template automatically creates tables on startup. Disable in production by removing `init_db()` from `main.py`.

## Configuration

All settings in `app/core/config.py` can be overridden via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_NAME` | Application name | FastAPI Template |
| `DEBUG` | Debug mode | True |
| `DATABASE_URL` | PostgreSQL connection | - |
| `REDIS_URL` | Redis connection | - |
| `SECRET_KEY` | JWT secret | - |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | 30 |
| `RATE_LIMIT_PER_MINUTE` | Rate limit | 60 |
| `TWO_FA_CODE_EXPIRE_MINUTES` | 2FA code TTL | 10 |
| `SMTP_HOST` | Email server | smtp.gmail.com |
| `SMTP_PORT` | Email port | 587 |

## Development

### Code Quality
```bash
# Format code
black .

# Lint
flake8 app/

# Type checking
mypy app/
```

### Testing
```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/

# Specific test
pytest tests/test_auth.py -v
```

## Production Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```bash
docker build -t my-fastapi-app .
docker run -p 8000:8000 --env-file .env my-fastapi-app
```

### Environment Checklist
- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY` (64+ characters)
- [ ] Configure proper `DATABASE_URL`
- [ ] Set production `REDIS_URL`
- [ ] Configure SMTP for emails
- [ ] Set appropriate `ALLOWED_ORIGINS`
- [ ] Use HTTPS
- [ ] Enable rate limiting
- [ ] Set up monitoring/logging
- [ ] Configure backup strategy

### Performance Tips
- Use connection pooling (configured by default)
- Enable Redis caching for frequently accessed data
- Use CDN for static assets
- Configure proper worker count (typically 2-4 × CPU cores)
- Monitor with tools like Prometheus/Grafana

## Troubleshooting

### Database Connection Issues
```bash
# Test connection
python -c "import asyncpg; asyncpg.connect('postgresql://...')"

# Check SSL requirement
# The template automatically handles SSL for cloud databases (Neon, etc.)
```

### Email Not Sending
```bash
# Test SMTP
curl -X POST "http://localhost:8000/api/v1/auth/test-2fa" \
  -H "Authorization: Bearer <token>"

# Check logs for errors
# Common issues: wrong credentials, blocked port 587, need app password
```

### Rate Limiting Issues
Disable temporarily:
```env
RATE_LIMIT_ENABLED=False
```

## Documentation

- [ROLES.md](ROLES.md) - Complete role-based access control guide
- [EMAIL_SETUP.md](EMAIL_SETUP.md) - Email and SMTP configuration
- [USER_SETTINGS.md](USER_SETTINGS.md) - User settings and 2FA management

## Stack

- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL with asyncpg
- **ORM**: SQLAlchemy 2.0 (async)
- **Cache**: Redis
- **Authentication**: JWT (python-jose), OAuth 2.0 (authlib)
- **Payments**: Stripe
- **Password Hashing**: bcrypt
- **Validation**: Pydantic v2
- **Email**: aiosmtplib
- **WebSockets**: FastAPI WebSocket support
- **Server**: Uvicorn

## License

MIT License - feel free to use this template for your projects!

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

- 📚 Documentation: Check the `/docs` folder
- 🐛 Issues: Open an issue on GitHub
- 💬 Discussions: Use GitHub Discussions

---

**Built with ❤️ using FastAPI**
