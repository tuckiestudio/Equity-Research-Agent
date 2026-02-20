# Sub-Agent Work Package: GLM — Stage 4 (App Shell + Portfolio Dashboard)

## Objective

Build the application shell (sidebar, header, auth), portfolio dashboard, API client layer, and global stores. This is the **foundation** all other frontend pages will plug into.

## Environment

- React 18 + TypeScript + Vite + Tailwind 3
- Already installed: `react-router-dom@6`, `axios`, `zustand@5`, `@tanstack/react-query@5`, `recharts`, `lucide-react`, `date-fns`, `clsx`
- Path alias: `@/` → `src/`
- API proxy: `/api` → `http://localhost:8000` (configured in `vite.config.ts`)
- DO NOT install new packages. Everything you need is already in `package.json`.
- Working dir: `/Users/bob/Projects/Equity-Research-Agent/frontend`

## Existing Code (DO NOT delete — extend)

```
src/
  main.tsx          — React DOM root + QueryClientProvider (keep as-is)
  App.tsx           — BrowserRouter + Routes (you will replace the routes)
  App.css           — minimal CSS (can be cleared)
  index.css         — Tailwind directives + base styles (extend, don't replace)
  services/api.ts   — axios instance baseURL="/api" (extend this)
  pages/Home.tsx    — health status page (replace with dashboard)
```

## Backend API Reference (all under `/api/v1/`)

### Auth
- `POST /auth/register` → `{ email, password, full_name }` → `{ id, email, token }`
- `POST /auth/login` → `{ email, password }` → `{ access_token, token_type }`
- `GET /auth/me` → `User` (requires `Authorization: Bearer <token>`)

### Stocks
- `GET /stocks/search?q=...` → `[{ ticker, name, exchange }]`
- `GET /stocks/{ticker}` → `Stock`

### Portfolios
- `GET /portfolios` → `[Portfolio]`
- `POST /portfolios` → `{ name, description }`
- `POST /portfolios/{id}/stocks` → `{ ticker }`
- `DELETE /portfolios/{id}/stocks/{ticker}`

### Health
- `GET /health` → `{ status, version }`

---

## Task 1: Design System (Tailwind Extension)

**File:** `src/index.css` — extend with dark-mode base styles

Update `tailwind.config.js`:
- Enable `darkMode: 'class'`
- Add semantic colors:
  ```
  surface: { DEFAULT: '#0f172a', card: '#1e293b', elevated: '#334155' }
  accent: { DEFAULT: '#6366f1', hover: '#818cf8', muted: '#4f46e5' }
  success: '#22c55e'
  warning: '#f59e0b'
  danger: '#ef4444'
  text: { primary: '#f1f5f9', secondary: '#94a3b8', muted: '#64748b' }
  border: { DEFAULT: '#334155', hover: '#475569' }
  ```

Update `index.css`:
- Add Google Font `Inter` import
- Set `dark` class on `<html>` by default
- Add utility classes for glassmorphism: `.glass { backdrop-filter: blur(12px); background: rgba(30,41,59,0.7); }`
- Add subtle animation keyframes for `fadeIn`, `slideUp`, `pulse-glow`

---

## Task 2: API Client

**File:** `src/services/api.ts` — extend existing

Add JWT interceptor:
```typescript
// Request interceptor: attach Bearer token from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor: redirect to /login on 401
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

**File:** `src/services/types.ts` — shared TypeScript types

```typescript
export interface User { id: string; email: string; full_name: string }
export interface Stock { id: string; ticker: string; company_name: string; sector?: string; industry?: string }
export interface Portfolio { id: string; name: string; description?: string; stocks: Stock[] }
export interface AuthResponse { access_token: string; token_type: string }
export interface StockSearchResult { ticker: string; name: string; exchange: string }
// Add more as needed for the pages you build
```

**File:** `src/services/auth.ts` — auth API functions
```typescript
export const login = (email: string, password: string) => api.post<AuthResponse>('/v1/auth/login', { email, password })
export const register = (email: string, password: string, full_name: string) => api.post('/v1/auth/register', { email, password, full_name })
export const getMe = () => api.get<User>('/v1/auth/me')
```

**File:** `src/services/stocks.ts` — stock API functions
**File:** `src/services/portfolios.ts` — portfolio API functions

---

## Task 3: Auth Store (Zustand)

**File:** `src/stores/auth.ts`

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      login: (token, user) => {
        localStorage.setItem('auth_token', token)
        set({ token, user, isAuthenticated: true })
      },
      logout: () => {
        localStorage.removeItem('auth_token')
        set({ token: null, user: null, isAuthenticated: false })
      },
      setUser: (user) => set({ user }),
    }),
    { name: 'auth-storage' }
  )
)
```

---

## Task 4: Layout Components

**File:** `src/components/layout/AppShell.tsx`
- Flex container: sidebar (fixed left, 260px) + main content area
- Dark background (`bg-surface`)
- Passes children to main content area

**File:** `src/components/layout/Sidebar.tsx`
- Logo/app name at top
- Navigation links with lucide-react icons:
  - Dashboard (`LayoutDashboard`)
  - Portfolio (`Briefcase`)
  - Search (`Search`)
- Bottom section: user avatar + name + logout
- Active link highlighting (use `useLocation()`)
- Subtle glassmorphism effect

**File:** `src/components/layout/Header.tsx`
- Shows page title (dynamic based on route)
- Right side: notification bell icon + user dropdown
- Subtle bottom border

---

## Task 5: Auth Pages

**File:** `src/pages/Login.tsx`
- Email + password form with validation
- Calls `POST /v1/auth/login`
- Stores token via `useAuthStore`
- Redirects to `/` on success
- Link to register page
- Dark themed, centered card with glassmorphism

**File:** `src/pages/Register.tsx`
- Full name + email + password + confirm password
- Calls `POST /v1/auth/register`
- Auto-login after registration
- Dark themed, matching Login style

**File:** `src/components/auth/ProtectedRoute.tsx`
- Wraps routes that require authentication
- Redirects to `/login` if not authenticated
- Calls `GET /v1/auth/me` on mount to validate token

---

## Task 6: Portfolio Dashboard

**File:** `src/pages/Dashboard.tsx`
- Grid of `StockCard` components showing user's portfolio stocks
- "Add Stock" button → opens `AddTickerModal`
- Empty state with illustration/prompt when no stocks added
- Uses `useQuery` to fetch portfolios

**File:** `src/components/dashboard/StockCard.tsx`
- Card showing: ticker, company name, sector
- Click navigates to `/stock/{ticker}`
- Subtle hover animation (scale + glow)
- Premium dark card with accent border

**File:** `src/components/dashboard/AddTickerModal.tsx`
- Modal overlay with search input
- Autocomplete: calls `GET /v1/stocks/search?q=...` with debounce
- Click result → calls `POST /v1/portfolios/{id}/stocks`
- Closes on success, invalidates portfolio query

---

## Task 7: App.tsx Router Update

Update `src/App.tsx` with all routes:

```tsx
<Router>
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/register" element={<Register />} />
    <Route element={<ProtectedRoute />}>
      <Route element={<AppShell />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/stock/:ticker" element={<StockDetail />} />
      </Route>
    </Route>
  </Routes>
</Router>
```

For `StockDetail` — just create a placeholder page:
```tsx
// src/pages/StockDetail.tsx
export default function StockDetail() {
  const { ticker } = useParams()
  return <div>Stock Detail: {ticker}</div>
}
```
(Codex will build this out with tabs in their spec.)

---

## Design Requirements

1. **Dark mode by default** — dark backgrounds, light text
2. **Premium feel** — glassmorphism cards, subtle animations, hover effects
3. **Professional typography** — Inter font, proper heading hierarchy
4. **Responsive** — works on 1280px+ screens (desktop-first, but don't break mobile)
5. **Consistent spacing** — use Tailwind spacing scale consistently
6. **All interactive elements** need hover/focus states
7. **Loading states** — skeleton loaders or spinner for async data
8. **Error states** — friendly error messages, not raw error text

## Constraints

1. Use ONLY packages already in `package.json`
2. Use the `@/` path alias for all imports
3. Keep components focused and reusable
4. Use `useQuery` / `useMutation` from react-query for all API calls
5. Test that the app builds: `cd frontend && npx tsc --noEmit` (no type errors)
