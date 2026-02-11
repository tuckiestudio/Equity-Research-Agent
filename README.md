# Equity Research Agent

AI-powered equity research and analysis platform.

## Project Structure

```
.
├── backend/          # FastAPI Python backend
│   ├── app/         # Application code
│   │   ├── api/     # API endpoints
│   │   ├── core/    # Configuration and core functionality
│   │   ├── models/  # Database models
│   │   ├── schemas/ # Pydantic schemas
│   │   └── services/ # Business logic
│   ├── tests/       # Test files
│   └── requirements.txt
├── frontend/         # React TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── stores/
│   │   └── types/
│   └── package.json
└── docs/            # Documentation
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (optional, for production)
- Redis (optional, for caching)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Development

### Backend

```bash
# Run tests
pytest

# Format code
black app tests

# Lint code
ruff check app tests

# Type check
mypy app
```

### Frontend

```bash
# Run tests
npm test

# Lint code
npm run lint

# Build for production
npm run build
```

## Features

- **AI-Powered Research**: Leverage Claude and GPT models for equity analysis
- **Real-time Data**: Integration with financial data sources
- **Modern UI**: Responsive React interface with Tailwind CSS
- **Type Safe**: Full TypeScript coverage on frontend, type hints on backend
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## License

ISC
