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
   python main.py
   ```
   Or with uvicorn directly:
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token

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
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./optimos.db
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

**⚠️ Important**: Change the `SECRET_KEY` in production!

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

## 📝 TODO

- [ ] Database integration (SQLAlchemy)
- [ ] Admin dashboard endpoints
- [ ] Stripe payment integration
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
