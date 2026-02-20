# Equity Research Agent — Project Instructions

## Overview
AI-powered equity research platform. FastAPI backend + React/Vite TypeScript frontend.

## Project Structure
```
backend/          FastAPI Python backend
  app/
    api/v1/       Versioned API endpoints
    core/         Config, logging, errors
    models/       SQLAlchemy models
    schemas/      Pydantic request/response schemas
    services/     Business logic
      data/       Financial data providers (hot-swappable)
      ai/         LLM providers (multi-model)
  tests/          Pytest test files
  alembic/        Database migrations

frontend/         React TypeScript frontend (Vite)
  src/
    components/   Reusable UI components
    pages/        Page-level components
    services/     API client layer
    hooks/        Custom React hooks
    stores/       Zustand state stores
    types/        TypeScript interfaces
```

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL, Redis
- **Frontend:** React 18, TypeScript, Vite, TanStack Query, Zustand, Recharts, Tailwind CSS
- **AI:** Multi-LLM (Claude, OpenAI, GLM-4.7, Kimi-K2.5) via provider abstraction
- **Data:** Hot-swappable providers (FMP, Finnhub, Alpha Vantage, yfinance, SEC EDGAR)

## Development Commands
```bash
# Start all services
docker compose up -d

# Backend
cd backend && uvicorn app.main:app --reload --port 8000
cd backend && pytest                    # Run tests
cd backend && black app tests           # Format
cd backend && ruff check app tests      # Lint
cd backend && mypy app                  # Type check
cd backend && alembic upgrade head      # Run migrations
cd backend && alembic revision --autogenerate -m "description"  # Create migration

# Frontend
cd frontend && npm run dev              # Dev server
cd frontend && npm test                 # Tests
cd frontend && npm run lint             # Lint
cd frontend && npm run build            # Build
```

## Architecture Conventions

### API Versioning
All endpoints must be under `/api/v1/`. Use FastAPI routers:
```python
router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])
```

### Data Providers
Financial data providers implement protocols in `app/services/data/protocols.py`. Active provider is set via `.env`:
```
FUNDAMENTALS_PROVIDER=fmp
PRICE_PROVIDER=finnhub
```
Never import a specific provider directly in business logic — use the registry.

### LLM Providers
AI providers implement the `LLMProvider` protocol in `app/services/ai/protocols.py`. Model routing is configured per task type.

### Error Handling
Use structured error responses:
```python
raise AppError(status_code=404, code="STOCK_NOT_FOUND", detail="Ticker XXXX not found")
```

### Database
- Always use async SQLAlchemy sessions
- All queries must be scoped to `user_id` (multi-user isolation)
- Use Alembic for ALL schema changes — never modify the DB manually

### Testing
- Tests go in `backend/tests/` mirroring the `app/` structure
- Use `pytest-asyncio` for async tests
- Mock external APIs (data providers, LLMs) in tests

## Code Style
- Backend: black + ruff + mypy (strict)
- Frontend: ESLint + TypeScript strict
- All functions must have type hints (backend) or TypeScript types (frontend)
- Docstrings on all public functions and classes
