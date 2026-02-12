# VaultVal

A full-stack application with a production-ready FastAPI backend, Next.js web frontend, and Expo mobile app.

## Repository Structure

```
vaultval/
  backend/    FastAPI REST API + WebSockets (Python)
  frontend/   Next.js 16 web application (React 19, Tailwind CSS 4)
  mobile/     Expo React Native mobile app
  admaker/    TypeScript ad creation tool
```

## Prerequisites

- **Backend:** Python 3.10+, PostgreSQL, Redis
- **Frontend:** Node.js 18+
- **Mobile:** Node.js 18+, Expo CLI

## Getting Started

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

Generate a secret key and configure your environment:

```bash
python setup_secret_key.py
```

Copy `.env.example` to `.env` and fill in your database, Redis, and other credentials:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<generated-from-setup-script>
```

Create the first superadmin user:

```bash
python setup_first_superadmin.py
```

Start the server:

```bash
python main.py
```

The API will be available at `http://localhost:8000`. Interactive docs at `/api/docs` (Swagger) and `/api/redoc`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:3000`.

### Mobile

```bash
cd mobile
npm install
npm start
```

Use the Expo Go app or run `npm run android` / `npm run ios` for platform-specific builds.

## Backend Overview

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| Database | PostgreSQL (SQLAlchemy 2.0 async + asyncpg) |
| Cache | Redis |
| Auth | JWT (python-jose), Google OAuth (authlib), 2FA, TOTP |
| Payments | Stripe (payments, subscriptions, Connect) |
| Background Tasks | Celery |
| Email | aiosmtplib |
| Push Notifications | Firebase Admin SDK |
| File Storage | Local or AWS S3 |
| Error Tracking | Sentry |

### API Endpoints

All routes are prefixed with `/api/v1`.

| Group | Prefix | Description |
|-------|--------|-------------|
| Auth | `/auth` | Register, login, Google OAuth, 2FA, TOTP |
| Users | `/users` | Profile management, role management |
| Health | `/health` | DB and cache connectivity checks |
| Stripe | `/stripe` | Payments, subscriptions, Connect, webhooks |
| Files | `/files` | File uploads |
| Notifications | `/notifications` | Push notifications |
| WebSocket | `/ws/{client_id}` | Real-time messaging and chat rooms |

### Role-Based Access Control

Three roles with hierarchical permissions:

- **User** -- Default role. View/edit own profile, enable 2FA.
- **Admin** -- View all users, manage users. Cannot change roles.
- **Superadmin** -- Full access including role management.

### Architecture

```
backend/app/
  api/
    routers/         Endpoint definitions
    dependencies/    Auth guards, pagination
    middleware/       Request logging
  core/              Config, database, cache, security, OAuth, Celery, Sentry
  db/
    models/          SQLAlchemy ORM models (User, AuditLog, Notification)
    schemas/         Pydantic request/response schemas
    utils/           Generic CRUD base class, user CRUD
  services/          Business logic (user, email, stripe, file, notification, totp, session, audit)
  middleware/        Rate limiting, correlation ID, security headers
  websockets/        Connection manager, WebSocket routes
  tasks/             Celery background tasks
  utils/             Logging, helpers, validators
```

### Optional Integrations

Each integration is toggled via environment variable and disabled by default:

| Feature | Environment Variable |
|---------|---------------------|
| Google OAuth | `GOOGLE_OAUTH_ENABLED` |
| Stripe Payments | `STRIPE_ENABLED` |
| Firebase Notifications | `FIREBASE_ENABLED` |
| S3 File Storage | `USE_S3` |
| Sentry Error Tracking | `SENTRY_ENABLED` |
| Rate Limiting | `RATE_LIMIT_ENABLED` |
| Audit Logging | `AUDIT_LOG_ENABLED` |

See `backend/.env.example` for the full list of configuration options.

## Frontend Overview

- **Framework:** Next.js 16 with App Router
- **Language:** TypeScript (strict mode)
- **Styling:** Tailwind CSS 4

## Mobile Overview

- **Framework:** Expo 54 with Expo Router (file-based routing)
- **Navigation:** Tab-based (React Navigation)
- **Language:** TypeScript (strict mode)

## Development

### Backend Code Quality

```bash
cd backend
black .              # Format
flake8 app/          # Lint
mypy app/            # Type check
pytest               # Run tests
```

### Frontend Lint

```bash
cd frontend
npm run lint
```

### Database Migrations

Tables are auto-created on startup in development. For production, use Alembic:

```bash
cd backend
alembic init alembic
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## License

MIT
