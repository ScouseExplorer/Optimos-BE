# Optimos Backend API

A robust FastAPI backend for a SaaS application with authentication, user management, and scalable architecture.

## 🚀 Features

- **FastAPI Framework** - High-performance async API
- **JWT Authentication** - Secure token-based auth
- **User Management** - Registration, login, and profile management
- **Modular Architecture** - Organized by feature domains
- **Type Safety** - Pydantic models for request/response validation
- **CORS Enabled** - Ready for frontend integration
- **Environment Configuration** - Easy configuration via .env files

## 📁 Project Structure

```
Optimos-BE/
├── app/
│   ├── api/routes/          # API endpoints
│   ├── auth/                # Authentication logic
│   ├── core/                # Configuration & security
│   ├── services/            # Business logic layer
│   ├── schemas/             # Pydantic models
│   ├── models/              # Database models
│   └── db/                  # Database configuration
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
└── .env.example            # Environment variables template
```

## 🛠️ Tech Stack

- **FastAPI** - Modern web framework
- **Pydantic** - Data validation
- **Python-Jose** - JWT token handling
- **Passlib** - Password hashing
- **Uvicorn** - ASGI server

## ⚡ Quick Start

### Prerequisites

- Python 3.12+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ScouseExplorer/Optimos-BE.git
   cd Optimos-BE
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1  # Windows
   source .venv/bin/activate    # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and update SECRET_KEY and other settings
   ```

5. **Run the server**
   ```bash
   alembic upgrade head
   python main.py
   ```
   Or with uvicorn directly:
   ```bash
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## 🐳 Docker Compose (API + PostgreSQL + Redis)

Run the full local stack with Docker Compose:

```bash
docker compose up --build -d
```

View logs:

```bash
docker compose logs -f api
```

Stop the stack:

```bash
docker compose down
```

For Compose, the API is configured to use internal PostgreSQL and Redis services via:

- `DATABASE_URL=postgresql://postgres:postgres@postgres:5432/optimos`
- `POSTGRES_DB=optimos`
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`

- `REDIS_ENABLED=true`
- `REDIS_URL=redis://redis:6379/0`

Redis is **required** when `ENVIRONMENT` is `production`/`prod`/`staging`: startup fails if `REDIS_ENABLED=false` or Redis is unreachable, so rate limits and token revocation are always shared across instances. In other environments the app logs a warning and falls back to per-process in-memory storage. `/health/ready` reports `redis: false` in prod-like environments if Redis isn't in use.
You can still run without Docker using the existing Python workflow.

## 📚 API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `POST /api/auth/email-verification/request` - Request an email verification link
- `POST /api/auth/email-verification/confirm` - Verify an email using `{ "token": "..." }`
- `POST /api/auth/password-reset/request` - Request a password reset link
- `POST /api/auth/password-reset/confirm` - Set a new password using `{ "token": "...", "password": "..." }`

New accounts remain inactive until the email address is verified. Password reset and verification links are single-use, expire after the configured lifetime, and are sent through Resend. Configure `RESEND_API_KEY`, `EMAIL_FROM` (a sender verified with Resend), and `FRONTEND_URL` (the frontend origin that handles `/verify-email` and `/reset-password`) before launch. Production/staging startup fails if email delivery is not configured or `FRONTEND_URL` is not a public HTTPS origin. Password reset invalidates existing login and refresh tokens.

### Users
- `GET /api/users/me` - Get current user profile (protected)
- `GET /api/users/{user_id}` - Get user by ID (protected)

### Health
- `GET /` - Welcome message
- `GET /health` - Health check endpoint

## 🔑 Environment Variables

Create a `.env` file based on `.env.example`:

```env
PROJECT_NAME=Optimos API
ENVIRONMENT=development
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
RESEND_API_KEY=re_...
EMAIL_FROM=Optimos <noreply@your-domain.example>
FRONTEND_URL=https://app.your-domain.example
DATABASE_URL=sqlite:///./optimos.db
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

For local PostgreSQL development, use:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/optimos
POSTGRES_DB=optimos
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

Registration and the email-action endpoints require a working Resend API key and a sender address verified with Resend, including in development. Without those settings they return `503` instead of creating an account that cannot receive its verification link.

### Startup Safety Checks

On startup, the API validates runtime configuration and fails fast for unsafe production/staging settings.
Examples of rejected production config include:

- default/short `SECRET_KEY`
- `AUTO_CREATE_TABLES=true`
- SQLite `DATABASE_URL`
- `LOG_LEVEL=DEBUG`

**⚠️ Important**: Change the `SECRET_KEY` in production!

## Stripe Integration (Where To Add It)

This backend already has billing entry points and credit-ledger handling. If you want to wire Stripe directly in this repo, implement it in these exact places:

1. Checkout session creation:
   - File: `app/services/billing_service.py`
   - Method: `BillingService.create_purchase_intent(...)`
   - Replace the current `BILLING_SERVICE_URL` proxy call with Stripe Checkout Session creation (or keep proxy mode and do it in your billing microservice).

2. Billing API endpoint surface:
   - File: `app/api/routes/billing.py`
   - Route: `POST /api/billing/purchase-intent`
   - Keep this as the frontend entrypoint. It should return `{ checkout_url, provider_intent_id }`.

3. Webhook verification + event handling:
   - File: `app/api/routes/billing.py`
   - Route: `POST /api/billing/webhooks`
   - Current mode (billing microservice): this route is an **internal** endpoint, not Stripe-facing. It does not (and cannot) verify Stripe signatures because Stripe never calls it. The billing service MUST verify the Stripe `Stripe-Signature` header with `STRIPE_WEBHOOK_SECRET` and confirm the payment succeeded *before* sending `credits.purchased` with the shared `X-Billing-Token` (compared in constant time). Keep the billing service private and `BILLING_WEBHOOK_TOKEN` secret and long/random; without it the route returns 503.
   - If switching to Stripe-native webhooks, verify Stripe signature here using `STRIPE_WEBHOOK_SECRET` instead of the shared token.

4. Credit application (idempotent):
   - File: `app/services/billing_service.py`
   - Method: `BillingService.apply_webhook_credit_event(...)`
   - Keep this method responsible for mapping provider events (e.g., `checkout.session.completed`) to credit grants.
   - It already calls idempotent credit application via `CreditService.apply_billing_purchase(...)`.

5. Ledger + wallet update logic:
   - File: `app/services/credit_service.py`
   - Method: `CreditService.apply_billing_purchase(...)`
   - This is the canonical place for wallet increment + replay protection.

6. DB replay safety:
   - File: `alembic/versions/20261020_0004_billing_purchase_uniqueness.py`
   - This migration adds DB-level uniqueness for billing purchase references.

### Recommended Stripe Event Mapping

- `checkout.session.completed` -> credits purchased event
- External or metadata field should include:
  - user id
  - credit amount
  - reference id (Stripe session/payment intent id)

### Required Env Vars For Stripe Direct Mode

Set these in `.env`:

```env
STRIPE_SECRET_KEY=sk_live_or_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_SUCCESS_URL=https://your-frontend/success
STRIPE_CANCEL_URL=https://your-frontend/cancel
```

If you keep the external billing microservice approach, continue using:

```env
BILLING_SERVICE_URL=https://your-billing-service
BILLING_WEBHOOK_TOKEN=your-internal-webhook-token
```

## 🧪 Development

### Project follows these principles:

- **Separation of Concerns** - Routes, services, and models are separated
- **Dependency Injection** - Services injected where needed
- **Type Hints** - Full type annotations for better IDE support
- **Async/Await** - Async endpoints for better performance

### Adding New Features

1. Create schemas in `app/schemas/`
2. Create service in `app/services/`
3. Create routes in `app/api/routes/`
4. Register router in `app/main.py`

### Database Migrations

Use Alembic for schema changes:

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

### Migrate from SQLite to PostgreSQL (local)

1. Start infra:
   ```bash
   docker compose up -d postgres redis
   ```
2. Update `.env` `DATABASE_URL` to PostgreSQL:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/optimos
   AUTO_CREATE_TABLES=false
   ```
3. Apply schema:
   ```bash
   alembic upgrade head
   ```
4. Run the API:
   ```bash
   uvicorn app.main:app --reload
   ```

If you need to migrate existing SQLite data, export/import rows with a one-time script per table (schema migrations create structure, not data copy).

This repo now includes a one-time helper script:

```bash
python scripts/migrate_sqlite_to_postgres.py --postgres-url "postgresql://postgres:postgres@localhost:5432/optimos"
```

Optional flags:

- `--sqlite-url "sqlite:///./optimos.db"` to choose a different source file
- `--keep-target-data` to skip target truncation before copy

## 📝 TODO

- [ ] Database integration (SQLAlchemy)
- [ ] Admin dashboard endpoints
- [ ] Stripe payment integration (see "Stripe Integration (Where To Add It)")
- [ ] Email notifications
- [ ] Rate limiting
- [ ] Unit tests
- [ ] Docker configuration
- [ ] CI/CD pipeline

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 👤 Author

**ScouseExplorer**

- GitHub: [@ScouseExplorer](https://github.com/ScouseExplorer)

---

Built with ❤️ using FastAPI
