# Trazio

Production-oriented web-first tourism platform.

---

## Architecture

API-first modular monolith (not microservices):

| Component | Technology |
|-----------|------------|
| Frontend | React + TypeScript + Vite |
| Backend | Python + FastAPI + Pydantic |
| Database | PostgreSQL + PostGIS |
| Cache | Redis |
| Maps | Mapbox (future) |
| Infrastructure | Docker Compose |
| CI | GitHub Actions |

---

## Repository Structure

```
trazio/
├── backend/                    # FastAPI backend
│   ├── app/                    # Application code
│   │   └── main.py            # FastAPI entry point
│   ├── tests/                 # Backend tests
│   │   ├── conftest.py        # Pytest fixtures
│   │   └── test_health.py     # Health endpoint tests
│   ├── Dockerfile             # Backend container
│   ├── pyproject.toml         # Python project configuration
│   └── alembic.ini            # Database migration configuration
│
├── frontend/                   # React + TypeScript frontend
│   ├── src/                    # Source code
│   │   ├── main.tsx           # Application entry
│   │   ├── App.tsx            # Root component
│   │   └── index.css          # Global styles
│   ├── public/                 # Static assets
│   │   └── index.html         # HTML entry point
│   ├── Dockerfile             # Frontend container
│   ├── package.json           # Node dependencies and scripts
│   └── vite.config.ts         # Vite configuration
│
├── database/                   # Database configuration
│   └── migrations/            # Alembic migration scripts
│
├── .github/                    # GitHub configuration
│   └── workflows/
│       └── ci.yml             # CI pipeline
│
├── docker-compose.yml          # Local development services
├── .env.example                # Environment variable template
├── .gitignore                  # Git ignore patterns
└── README.md                   # This file
```

---

## Development Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| (Optional) Python | 3.11+ | Local backend development |
| (Optional) Node.js | 20+ | Local frontend development |

---

## Local Development

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd trazio

# Copy environment template
cp .env.example .env

# Optionally edit .env with local overrides

# Start all services (backend, frontend, postgres, redis)
docker compose up -d

# View logs
docker compose logs -f

# Run backend tests
docker compose exec backend pytest tests/ -v

# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```

Services will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Health: http://localhost:8000/health

### Without Docker (Direct Local Development)

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Current Status

**Phase 1A: Infrastructure Setup**

🚧 The project is currently in infrastructure setup phase. Core development dependencies, containerization, and CI foundations are being established. No product features, business logic, authentication, or external service integrations (Mapbox, AI/ML, optimization) have been implemented yet.

---

## Project Commands

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start all development services |
| `docker compose down` | Stop all services |
| `docker compose logs -f backend` | View backend logs |
| `docker compose exec backend pytest` | Run backend tests |
