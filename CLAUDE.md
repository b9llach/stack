# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VaultVal is a full-stack monorepo with four projects:
- **backend/** - FastAPI Python REST API + WebSockets (the core of the project)
- **frontend/** - Next.js 16 web application (React 19, Tailwind CSS 4)
- **mobile/** - Expo React Native app (Expo 54, Expo Router)
- **admaker/** - TypeScript ad creation tool (minimal/early stage)

## Common Commands

### Backend (from `backend/`)
```bash
# Setup
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python setup_secret_key.py     # Generate SECRET_KEY
python setup_first_superadmin.py  # Create first superadmin user

# Run
python main.py
# or: uvicorn main:app --reload

# Code quality
black .                        # Format
flake8 app/                    # Lint
mypy app/                      # Type check

# Tests
pytest                         # All tests
pytest tests/test_auth.py -v   # Single test file
pytest --cov=app tests/        # With coverage
```

### Frontend (from `frontend/`)
```bash
npm run dev       # Dev server on localhost:3000
npm run build     # Production build
npm run lint      # ESLint
```

### Mobile (from `mobile/`)
```bash
npm start         # Expo dev server
npm run android   # Android
npm run ios       # iOS
```

## Backend Architecture

The backend uses a layered architecture under `backend/app/`:

- **`api/routers/`** - Endpoint definitions. All routes prefixed with `/api/v1`. Routers: auth, users, health, stripe, files, notifications.
- **`api/dependencies/`** - FastAPI dependency injection: auth guards (`get_current_user`, `get_current_admin_user`, `get_current_superadmin_user`), pagination.
- **`services/`** - Business logic layer. Each service handles a domain: user, email, stripe, file, notification, totp, session, audit.
- **`db/models/`** - SQLAlchemy 2.0 async ORM models. User is the primary model; also AuditLog, Notification. Roles defined in `enums.py` (USER, ADMIN, SUPERADMIN).
- **`db/schemas/`** - Pydantic v2 request/response schemas.
- **`db/utils/`** - Generic CRUD base class (`crud.py`) and user-specific CRUD (`user_crud.py`).
- **`core/`** - Infrastructure: config (Pydantic Settings), async database setup (asyncpg with auto SSL for Neon), Redis cache, JWT security, OAuth, Celery, Sentry.
- **`middleware/`** - Rate limiting, correlation ID (request tracing), security headers.
- **`websockets/`** - Connection manager with room support, WebSocket router.
- **`tasks/`** - Celery background tasks for email, files, notifications.

### Key Patterns
- Fully async throughout (asyncpg, redis.asyncio, aiosmtplib)
- JWT auth with refresh tokens; role-based access control (USER < ADMIN < SUPERADMIN)
- Google OAuth via authlib; optional per-user 2FA (email) and TOTP (authenticator app)
- Brute-force protection on login and 2FA endpoints
- Config via environment variables loaded through Pydantic Settings (`app/core/config.py`)
- Tables auto-created on startup in dev; Alembic recommended for production migrations

### Database
- PostgreSQL with SQLAlchemy 2.0 async + asyncpg
- Neon-compatible (automatic SSL detection)
- Connection string format: `postgresql+asyncpg://user:password@host:5432/dbname`
- When modifying models, provide the corresponding SQL for Neon DB

### External Integrations (all optional, toggled via env vars)
- **Stripe**: Payments, subscriptions, Connect (`STRIPE_ENABLED`)
- **Google OAuth**: Social login (`GOOGLE_OAUTH_ENABLED`)
- **Firebase**: Push notifications (`FIREBASE_ENABLED`)
- **S3**: Cloud file storage (`USE_S3`)
- **Sentry**: Error tracking (`SENTRY_ENABLED`)
- **Celery + Redis**: Background task processing
- **Redis**: Caching and session storage

## Frontend Architecture

Next.js 16 with App Router in `frontend/src/app/`. TypeScript strict mode. Tailwind CSS 4 for styling. Path alias `@/*` maps to project root.

## Mobile Architecture

Expo 54 with file-based routing via Expo Router. Tab navigation (home, explore). React Native 0.81 with Reanimated and Gesture Handler.

## API Documentation

When the backend is running: Swagger UI at `/api/docs`, ReDoc at `/api/redoc`.

## Environment

Backend config lives in `backend/.env` (see `backend/.env.example` for all variables). Key required vars: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`.

## Style Guidelines

- No emojis in print statements, UI, or code
- Professional UI design and logging
- Ensure frontend/mobile projects build successfully before considering work complete
