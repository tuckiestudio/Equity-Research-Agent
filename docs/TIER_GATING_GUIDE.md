# Tier Gating System - Usage Guide

## Overview

The Equity Research Agent now includes a comprehensive tier-based access control system. This allows you to restrict features based on user subscription tiers (Free, Pro, Premium).

## Tiers and Features

### User Tiers

- **FREE**: Basic access for new users
- **PRO**: Enhanced features ($29/month)
- **PREMIUM**: Full access including AI features ($99/month)

### Feature Matrix

| Feature | FREE | PRO | PREMIUM |
|---------|------|-----|---------|
| Stock Search | ✅ | ✅ | ✅ |
| Stock Detail | ✅ | ✅ | ✅ |
| Portfolios (Basic) | ✅ | ✅ | ✅ |
| DCF Model (Basic) | ✅ | ✅ | ✅ |
| Research Notes | ✅ | ✅ | ✅ |
| Watch Lists | ✅ | ✅ | ✅ |
| Stock Fundamentals | ❌ | ✅ | ✅ |
| Stock News | ❌ | ✅ | ✅ |
| Multiple Portfolios | ❌ | ✅ | ✅ |
| DCF Custom Assumptions | ❌ | ✅ | ✅ |
| DCF Scenarios | ❌ | ✅ | ✅ |
| Comps Analysis | ❌ | ✅ | ✅ |
| AI Sentiment Analysis | ❌ | ✅ | ✅ |
| Historical Data | ❌ | ✅ | ✅ |
| AI Thesis Generation | ❌ | ❌ | ✅ |
| AI News Analysis | ❌ | ❌ | ✅ |
| Real-time Data | ❌ | ❌ | ✅ |
| Analyst Estimates | ❌ | ❌ | ✅ |
| Portfolio Export | ❌ | ❌ | ✅ |
| Alerts | ❌ | ❌ | ✅ |

### Usage Limits

| Resource | FREE | PRO | PREMIUM |
|----------|------|-----|---------|
| Max Portfolios | 1 | 5 | Unlimited |
| Max Stocks per Portfolio | 10 | 50 | Unlimited |
| Max Watch Lists | 1 | 10 | Unlimited |
| Max Notes per Stock | 5 | 50 | Unlimited |
| API Calls per Day | 100 | 1,000 | Unlimited |

## Implementation Guide

### 1. Basic Tier Protection

To require a minimum tier for an endpoint:

```python
from fastapi import Depends
from app.api.deps import get_current_user
from app.services.permissions import Tier, create_require_tier_dependency

@router.get("/pro-feature")
async def pro_feature(
    user: User = Depends(get_current_user),
    _=Depends(create_require_tier_dependency(Tier.PRO)),
):
    return {"message": "This is a Pro feature"}
```

### 2. Feature-Based Protection

To require access to a specific feature:

```python
from app.services.permissions import Feature, create_require_feature_dependency

@router.post("/scenarios")
async def create_scenario(
    data: ScenarioRequest,
    user: User = Depends(get_current_user),
    _=Depends(create_require_feature_dependency(Feature.DCF_SCENARIOS)),
):
    # Only Pro and Premium users can access
    return create_scenario_logic(data, user)
```

### 3. Using Pre-configured Dependencies

For convenience, common requirements have pre-configured dependencies:

```python
from app.services.permissions import (
    require_pro,           # Pro tier or higher
    require_premium,       # Premium tier only
    require_dcf_custom,    # Custom DCF assumptions
    require_scenarios,     # DCF scenarios
    require_comps,         # Comparable companies
    require_ai_thesis,     # AI thesis generation
    require_portfolio_export,  # Portfolio export
    require_alerts,        # Alerts/notifications
)

@router.get("/advanced-dcf")
async def advanced_dcf(
    user: User = Depends(get_current_user),
    _=Depends(require_dcf_custom),
):
    return advanced_dcf_logic()
```

### 4. Programmatic Feature Checking

To check feature access without blocking:

```python
from app.services.permissions import has_feature_access, Feature

@router.get("/feature-status")
async def check_feature(
    user: User = Depends(get_current_user),
):
    can_use_scenarios = has_feature_access(user, Feature.DCF_SCENARIOS)

    return {
        "can_create_scenarios": can_use_scenarios,
        "upgrade_message": "Upgrade to Pro for scenarios" if not can_use_scenarios else None
    }
```

### 5. Checking Usage Limits

To enforce tier-based limits:

```python
from app.services.permissions import check_limits

@router.post("/portfolios")
async def create_portfolio(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    max_portfolios = check_limits(user, "portfolios")

    # Count existing portfolios
    existing_count = await count_user_portfolios(user.id, db)

    if max_portfolios != -1 and existing_count >= max_portfolios:
        raise AppError(
            403,
            "LIMIT_REACHED",
            f"Maximum {max_portfolios} portfolios allowed for {user.tier} tier"
        )

    return await create_portfolio_logic(user, db)
```

## API Endpoints

### User Tier Information

Get current user's tier and limits:

```bash
GET /api/v1/tiers/my-limits
Authorization: Bearer <token>
```

Response:
```json
{
  "tier": "pro",
  "max_portfolios": 5,
  "max_stocks_per_portfolio": 50,
  "max_watch_lists": 10,
  "max_notes_per_stock": 50,
  "api_calls_per_day": 1000
}
```

### Check Feature Access

Check if user has access to a specific feature:

```bash
GET /api/v1/tiers/user?user_id=<user_id>
Authorization: Bearer <token>
```

### Admin: Update User Tier

```bash
POST /api/v1/tiers/admin/update-user-tier?user_id=<user_id>
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "tier": "pro",
  "reason": "User upgraded via Stripe"
}
```

## Error Responses

### Insufficient Tier Error

When a user tries to access a feature above their tier:

```json
{
  "code": "INSUFFICIENT_TIER",
  "detail": "This feature requires pro tier or higher. Your current tier: free.",
  "status_code": 403
}
```

### Feature Not Available Error

When a specific feature is not available:

```json
{
  "code": "FEATURE_NOT_AVAILABLE",
  "detail": "The 'dcf_custom_assumptions' feature is not available in your current tier. Upgrade to Pro or Premium to access this feature.",
  "status_code": 403
}
```

## Frontend Integration

### Display User Tier

The `/api/v1/auth/me` endpoint now includes the user's tier:

```typescript
interface User {
  id: string
  email: string
  full_name: string
  tier: 'free' | 'pro' | 'premium'
}
```

### Check Feature Access in Frontend

```typescript
const TIER_FEATURES = {
  free: ['stock_search', 'stock_detail', 'portfolio_create'],
  pro: [...FREE_FEATURES, 'dcf_scenarios', 'comps_analysis'],
  premium: [...PRO_FEATURES, 'ai_thesis_generation', 'alerts']
}

function hasFeatureAccess(user: User, feature: string): boolean {
  return TIER_FEATURES[user.tier]?.includes(feature) ?? false
}

// Usage
if (hasFeatureAccess(user, 'dcf_scenarios')) {
  // Show scenarios button
}
```

### Show Upgrade Prompts

```typescript
function showUpgradePrompt(requiredTier: string) {
  return (
    <div className="upgrade-prompt">
      <p>This feature requires {requiredTier} tier</p>
      <button onClick={() => navigate('/upgrade')}>
        Upgrade Now
      </button>
    </div>
  )
}
```

## Testing

### Test Permissions

```bash
cd backend
pytest tests/test_permissions.py -v
```

### Test Tier-Protected Endpoints

```bash
# Test with free user
curl -X GET http://localhost:8000/api/v1/scenarios-protected/pro-feature \
  -H "Authorization: Bearer <free_user_token>"

# Expected: 403 Forbidden

# Test with pro user
curl -X GET http://localhost:8000/api/v1/scenarios-protected/pro-feature \
  -H "Authorization: Bearer <pro_user_token>"

# Expected: 200 OK
```

## Migration

### Add Tier Column to Users Table

The `tier` column should already exist in the `users` table. If not, create a migration:

```bash
cd backend
alembic revision --autogenerate -m "Add tier column to users"
alembic upgrade head
```

### Set Default Tier for Existing Users

```python
UPDATE users SET tier = 'free' WHERE tier IS NULL;
```

## Admin Management

### Check User Tier

```python
from app.services.permissions import Tier, check_limits

user = await get_user(user_id)
print(f"User tier: {user.tier}")
print(f"Max portfolios: {check_limits(user, 'portfolios')}")
```

### Upgrade User Tier

```python
user.tier = Tier.PRO.value
await db.commit()
```

## Best Practices

1. **Always use feature-based checks** rather than tier-based when possible. This makes it easier to adjust features across tiers later.

2. **Provide clear upgrade paths** in error messages so users know what they need to upgrade.

3. **Check limits before resource creation** to prevent users from hitting limits mid-operation.

4. **Log tier changes** for audit purposes (especially for compliance).

5. **Consider grace periods** when downgrading users (e.g., don't immediately delete data over limits).

## Future Enhancements

- [ ] Stripe integration for automatic tier management
- [ ] Trial periods for Pro/Premium features
- [ ] Tier-specific rate limiting
- [ ] Usage analytics and reporting
- [ ] Promo codes and discounts
- [ ] Team/enterprise tiers with shared limits
