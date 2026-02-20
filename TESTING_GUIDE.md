# Equity Research Agent - Testing Guide

**Last Updated:** 2026-02-18
**Purpose:** Step-by-step guide to test all features via browser

---

## Quick Start - Run Everything

### Option 1: Docker Compose (Recommended)

```bash
# 1. Navigate to project root
cd /Users/bob/Projects/Equity-Research-Agent

# 2. Create .env file with secure values
cp backend/.env.example backend/.env

# Generate SECRET_KEY (must be 32+ chars)
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" >> backend/.env

# 3. Set database password in .env
echo "POSTGRES_PASSWORD=your_secure_password_here" >> backend/.env

# 4. Start all services
docker compose up -d

# 5. Check services are running
docker compose ps

# 6. View logs (optional)
docker compose logs -f backend
```

### Option 2: Manual Setup (Development)

#### Backend
```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

#### Frontend (new terminal)
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

---

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | Main application UI |
| **Backend API** | http://localhost:8000 | REST API |
| **API Docs** | http://localhost:8000/api/v1/docs | Swagger/OpenAPI documentation |
| **Database** | localhost:5432 | PostgreSQL |
| **Redis** | localhost:6379 | Cache |

---

## Feature Testing Checklist

### 1. Authentication Flow ✅

#### Register New User
1. Go to http://localhost:5173
2. Click "Register" or navigate to `/register`
3. Fill in:
   - Email: `test@example.com`
   - Password: `testpassword123` (min 8 chars)
   - Full Name: `Test User`
4. Click "Register"
5. **Expected:** Redirected to dashboard, token stored

#### Login
1. Navigate to `/login`
2. Enter credentials from registration
3. Click "Login"
4. **Expected:** Redirected to dashboard

#### Test Rate Limiting
```bash
# Run 6 rapid login attempts (6th should fail with 429)
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}' \
    -w "Request $i: %{http_code}\n"
done
```

---

### 2. Dashboard & Portfolio Management ✅

#### Create Portfolio
1. After login, you're on Dashboard
2. Click "Add Portfolio" or "Create New"
3. Enter portfolio name: `My First Portfolio`
4. Click "Create"
5. **Expected:** Portfolio appears in list

#### Add Stock to Portfolio
1. In your portfolio, click "Add Stock"
2. Search for a ticker: `AAPL`
3. Select from results
4. Enter quantity: `10`
5. Click "Add"
6. **Expected:** Stock appears in portfolio with current price

#### Test Tier Limits (Free Tier)
1. Try to create a 2nd portfolio
2. **Expected:** Error message about tier limit (Free = 1 portfolio max)

---

### 3. Stock Search & Details ✅

#### Search Stocks
1. Use search bar in header or dashboard
2. Type: `AAPL` or `Apple`
3. **Expected:** Dropdown with matching stocks

#### View Stock Details
1. Click on a stock from search or portfolio
2. Navigate to `/stock/AAPL`
3. **Expected to see:**
   - Company profile
   - Current price
   - Price chart
   - Fundamentals (P/E, Market Cap, etc.)
   - Recent news
   - Analyst estimates

---

### 4. DCF Valuation Model ✅

#### Create DCF Model
1. From stock detail page, click "DCF Model" or "Valuation"
2. **Expected:** DCF model with default assumptions

#### Customize Assumptions (Pro Feature)
1. Try to modify:
   - Revenue growth rate
   - Terminal growth rate
   - Discount rate (WACC)
2. **Free tier:** Should see upgrade prompt
3. **Pro/Premium:** Changes should apply, valuation updates

#### Export Model
1. Click "Export" or "Download"
2. **Expected:** Excel/PDF download (Premium feature)

---

### 5. Scenario Analysis ✅

#### Create Scenario
1. From DCF model, click "Scenarios" tab
2. Click "Add Scenario"
3. Name: `Bull Case`
4. Set assumptions: Higher growth, lower discount rate
5. Click "Save"
6. **Expected:** Scenario saved, valuation updates

#### Compare Scenarios
1. Create 3 scenarios: Bull, Base, Bear
2. **Expected:** Side-by-side comparison table

---

### 6. Comparable Company Analysis ✅

#### Add Comps
1. From stock detail, click "Comps" tab
2. Click "Add Comparable"
3. Search and add competitors: `MSFT`, `GOOGL`, `META`
4. **Expected:** Comparison table with valuation multiples

#### View Multiples
- P/E ratios
- EV/EBITDA
- P/S ratios
- **Expected:** Industry comparison

---

### 7. AI Thesis Generation ✅

#### Generate Thesis (Premium Feature)
1. From stock detail, click "AI Thesis" or "Research"
2. Click "Generate Thesis"
3. **Free/Pro tier:** Should see upgrade prompt
4. **Premium:** AI-generated investment thesis appears

#### View Sentiment Analysis
1. Check news sentiment scores
2. **Expected:** Bullish/Bearish/Neutral indicators

---

### 8. Research Notes ✅

#### Create Note
1. From stock detail, click "Notes" tab
2. Click "Add Note"
3. Write analysis
4. Click "Save"
5. **Expected:** Note saved, appears in list

#### Tier Limit Test
1. Free tier: Create 6 notes on same stock
2. **Expected:** Error on 6th note (limit = 5)

---

### 9. Watch Lists ✅

#### Create Watch List
1. Navigate to "Watchlists" from menu
2. Click "Create Watchlist"
3. Name: `Tech Stocks`
4. Add stocks: `AAPL`, `MSFT`, `NVDA`
5. **Expected:** Watchlist created with stocks

---

### 10. Export Functionality ✅

#### Export Portfolio (Premium)
1. From portfolio view, click "Export"
2. Choose format: Excel/CSV
3. **Free/Pro:** Upgrade prompt
4. **Premium:** Download starts

---

## Backend API Testing

### Test with curl

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"api@test.com","password":"testpass123","full_name":"API Test"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"api@test.com","password":"testpass123"}'

# Save the access_token from response

# 3. Get current user
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# 4. Search stocks
curl -X GET "http://localhost:8000/api/v1/stocks/search?q=AAPL" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# 5. Get stock details
curl -X GET "http://localhost:8000/api/v1/stocks/AAPL" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# 6. Get my tier limits
curl -X GET http://localhost:8000/api/v1/tiers/my-limits \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Test with Swagger UI

1. Open http://localhost:8000/api/v1/docs
2. Click "Authorize" button
3. Login via `/api/v1/auth/login` endpoint
4. Copy token
5. Paste into authorize dialog
6. Test all endpoints interactively

---

## E2E Automated Tests

### Run Playwright Tests

```bash
cd frontend

# Install browsers (first time only)
npm run test:e2e:install

# Run all E2E tests (headless)
npm run test:e2e

# Run with UI (interactive)
npm run test:e2e:ui

# Run specific test file
npm run test:e2e e2e/auth.spec.ts

# Run with visible browser
npm run test:e2e:headed

# View HTML report
npm run test:e2e:report
```

### Test Coverage

| Test File | What It Tests |
|-----------|---------------|
| `e2e/auth.spec.ts` | Registration, login, logout |
| `e2e/critical-path.spec.ts` | Full user journey |
| `e2e/mocked-critical-path.spec.ts` | Mocked API tests |

---

## Unit Tests

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend

# Run all unit tests
npm run test

# Run in watch mode
npm run test -- --watch

# Run with coverage
npm run test -- --coverage
```

---

## Troubleshooting

### Backend won't start

```bash
# Check SECRET_KEY
cd backend
python3 -c "from app.core.config import settings; print('OK')"

# If error, add SECRET_KEY to .env
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env

# Check database connection
docker compose logs db
```

### Frontend won't start

```bash
cd frontend
npm install
npm run dev
```

### Database errors

```bash
# Reset database (Docker)
docker compose down -v
docker compose up -d db
sleep 5
cd backend
alembic upgrade head
```

### Rate limiting not working

```bash
# Verify slowapi installed
pip list | grep slowapi

# Check limiter in main.py
grep -n "limiter" backend/app/main.py
```

---

## Admin Features

### Create Admin User

```bash
# 1. Set admin email in .env
echo "ADMIN_EMAILS=admin@example.com" >> backend/.env

# 2. Restart backend
docker compose restart backend

# 3. Register with admin email
# User will automatically get is_admin flag

# 4. Verify in database
docker compose exec db psql -U equity_user -d equity_research \
  -c "SELECT email, is_admin FROM users;"
```

### Admin Endpoints

```bash
# Update user tier
curl -X POST http://localhost:8000/api/v1/tiers/admin/update-user-tier \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_email":"user@example.com","tier":"premium"}'

# List users by tier
curl -X GET "http://localhost:8000/api/v1/tiers/admin/users-by-tier?tier=premium" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## Performance Testing

### Load Test with Apache Bench

```bash
# Test search endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/stocks/search?q=AAPL"
```

### Test Rate Limiting

```bash
# Should see 429 after 5 requests
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrong"}'
done
```

---

## Security Testing

### Run Security Scan

```bash
cd backend
pip install bandit
bandit -r app -ll
```

### Test CORS

```bash
curl -X OPTIONS http://localhost:8000/api/v1/stocks \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -v 2>&1 | grep "Access-Control"
```

### Test JWT Validation

```bash
# Use invalid token
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer invalid_token_here"
# Expected: 401 Unauthorized
```

---

## Checklist Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Register | ⬜ | |
| Login | ⬜ | |
| Rate Limiting | ⬜ | Test with curl loop |
| Dashboard | ⬜ | |
| Create Portfolio | ⬜ | |
| Add Stock | ⬜ | |
| Stock Search | ⬜ | |
| Stock Details | ⬜ | |
| DCF Model | ⬜ | |
| Scenarios | ⬜ | Pro feature |
| Comps | ⬜ | Pro feature |
| AI Thesis | ⬜ | Premium feature |
| Research Notes | ⬜ | |
| Watch Lists | ⬜ | |
| Export | ⬜ | Premium feature |
| Tier Limits | ⬜ | Test limits |
| Admin Features | ⬜ | Requires admin user |

---

## Next Steps

1. **Run the application** using Docker or manual setup
2. **Complete the checklist** above
3. **Report any issues** found during testing
4. **Run automated tests** to verify functionality

---

**For questions or issues, refer to:**
- `AGENT_HANDOFF.md` - General project context
- `SECURITY_REMEDIATION.md` - Security details
- `CLAUDE.md` - Architecture conventions
