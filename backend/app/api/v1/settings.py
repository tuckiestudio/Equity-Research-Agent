"""User settings API endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    fundamentals_provider: Optional[str] = None
    price_provider: Optional[str] = None
    profile_provider: Optional[str] = None
    news_provider: Optional[str] = None
    fmp_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    eodhd_api_key: Optional[str] = None
    polygon_api_key: Optional[str] = None
    alpha_vantage_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

class SettingsResponse(BaseModel):
    fundamentals_provider: str
    price_provider: str
    profile_provider: str
    news_provider: str
    fmp_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    eodhd_api_key: Optional[str] = None
    polygon_api_key: Optional[str] = None
    alpha_vantage_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    model_config = {"from_attributes": True}

@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
) -> SettingsResponse:
    """Get the current user's settings."""
    return current_user.settings

@router.put("", response_model=SettingsResponse)
async def update_settings(
    update_data: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Update the current user's settings."""
    settings = current_user.settings
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(settings, key, value)
        
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    
    return settings
