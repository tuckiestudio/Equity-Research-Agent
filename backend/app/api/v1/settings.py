"""User settings API endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])


def mask_api_key(key: Optional[str]) -> Optional[str]:
    """Mask an API key for display, showing only first 4 and last 4 characters.

    Args:
        key: The API key to mask

    Returns:
        Masked key (e.g., 'sk-a...xyz') or None if key is None/empty
    """
    if not key:
        return None
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


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
    glm_api_key: Optional[str] = None
    kimi_api_key: Optional[str] = None


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
    glm_api_key: Optional[str] = None
    kimi_api_key: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator(
        "fmp_api_key",
        "finnhub_api_key",
        "eodhd_api_key",
        "polygon_api_key",
        "alpha_vantage_api_key",
        "openai_api_key",
        "anthropic_api_key",
        "glm_api_key",
        "kimi_api_key",
        mode="before",
    )
    @classmethod
    def mask_api_keys(cls, v: Optional[str]) -> Optional[str]:
        """Mask API keys in the response for security."""
        return mask_api_key(v)


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
) -> SettingsResponse:
    """Get the current user's settings.

    API keys are returned masked for security (e.g., 'sk-a...xyz').
    """
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
