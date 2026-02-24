"""User settings API endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.core.logging import get_logger
from app.services.llm.types import TaskType

logger = get_logger(__name__)

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


class ModelRoute(BaseModel):
    """A single model route for a task type."""
    provider: str
    model: str


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
    openrouter_api_key: Optional[str] = None
    chutes_api_key: Optional[str] = None
    llm_routing_preferences: Optional[dict[str, ModelRoute]] = None


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
    openrouter_api_key: Optional[str] = None
    chutes_api_key: Optional[str] = None
    llm_routing_preferences: Optional[dict[str, ModelRoute]] = None

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
        "openrouter_api_key",
        "chutes_api_key",
        mode="before",
    )
    @classmethod
    def mask_api_keys(cls, v: Optional[str]) -> Optional[str]:
        """Mask API keys in the response for security."""
        return mask_api_key(v)


class ProviderInfo(BaseModel):
    """Information about an LLM provider."""
    name: str
    display_name: str
    description: str
    models: list[str]
    has_api_key: bool = False


class TaskTypeInfo(BaseModel):
    """Information about a task type."""
    type: str
    name: str
    description: str
    default_provider: str
    default_model: str


@router.get("/llm-providers", response_model=list[ProviderInfo])
async def get_llm_providers(
    current_user: User = Depends(get_current_user),
) -> list[ProviderInfo]:
    """Get available LLM providers and their models.

    Includes information about which providers have API keys configured.
    """
    from app.core.config import settings
    from app.services.llm.router import OPENROUTER_MODEL_MAP, CHUTES_MODEL_MAP

    # Check which API keys are available (user or global)
    user_settings = current_user.settings if hasattr(current_user, 'settings') else None

    def has_key(user_key: Optional[str], global_key: str) -> bool:
        return bool(user_key or global_key)

    providers = []

    # Anthropic
    anthropic_key = (user_settings.anthropic_api_key if user_settings else None) or settings.ANTHROPIC_API_KEY
    if anthropic_key:
        providers.append(ProviderInfo(
            name="anthropic",
            display_name="Anthropic",
            description="Claude models - excellent for reasoning and analysis",
            models=["claude-sonnet-4-20250514", "claude-3-opus", "claude-3-haiku"],
            has_api_key=True
        ))

    # OpenAI
    openai_key = (user_settings.openai_api_key if user_settings else None) or settings.OPENAI_API_KEY
    if openai_key:
        providers.append(ProviderInfo(
            name="openai",
            display_name="OpenAI",
            description="GPT-4 and GPT-4o models - fast and capable",
            models=["gpt-4o", "gpt-4-turbo", "gpt-4o-mini", "gpt-3.5-turbo"],
            has_api_key=True
        ))

    # GLM
    glm_key = (user_settings.glm_api_key if user_settings else None) or settings.GLM_API_KEY
    if glm_key:
        providers.append(ProviderInfo(
            name="glm",
            display_name="Z.ai (GLM)",
            description="GLM-4 models from Zhipu AI",
            models=["glm-4", "glm-4-flash"],
            has_api_key=True
        ))

    # Kimi
    kimi_key = (user_settings.kimi_api_key if user_settings else None) or settings.KIMI_API_KEY
    if kimi_key:
        providers.append(ProviderInfo(
            name="kimi",
            display_name="Moonshot (Kimi)",
            description="Kimi-K2.5 models - strong at long context",
            models=["kimi-k2.5", "kimi-flash"],
            has_api_key=True
        ))

    # OpenRouter - meta-provider with many models
    openrouter_key = (user_settings.openrouter_api_key if user_settings else None) or settings.OPENROUTER_API_KEY
    if openrouter_key:
        providers.append(ProviderInfo(
            name="openrouter",
            display_name="OpenRouter",
            description="100+ models: Claude, GPT-4, Llama, Mistral, Gemini & more (FREE models available!)",
            models=[
                # === FREE MODELS ===
                "meta-llama/llama-3-8b-instruct:free",
                "google/gemma-7b-it:free",
                "mistralai/mistral-7b-instruct:free",
                # === PREMIUM MODELS ===
                "anthropic/claude-3-opus",
                "anthropic/claude-3-sonnet",
                "anthropic/claude-3-haiku",
                "openai/gpt-4o",
                "openai/gpt-4-turbo",
                "openai/gpt-4o-mini",
                "meta-llama/llama-3-70b-instruct",
                "meta-llama/llama-3-8b-instruct",
                "mistralai/mistral-large",
                "mistralai/mixtral-8x7b-instruct",
                "google/gemini-pro-1.5",
            ],
            has_api_key=True
        ))

    # Chutes - open-source models
    chutes_key = (user_settings.chutes_api_key if user_settings else None) or settings.CHUTES_API_KEY
    if chutes_key:
        providers.append(ProviderInfo(
            name="chutes",
            display_name="Chutes.ai",
            description="Fast open-source models: Llama, Mistral, Qwen",
            models=[
                "llama-3-70b-instruct",
                "llama-3-8b-instruct",
                "llama-3.1-70b-instruct",
                "llama-3.1-8b-instruct",
                "mixtral-8x7b-instruct",
                "qwen-2.5-72b-instruct",
            ],
            has_api_key=True
        ))

    return providers


@router.get("/llm-task-types", response_model=list[TaskTypeInfo])
async def get_llm_task_types(
    current_user: User = Depends(get_current_user),
) -> list[TaskTypeInfo]:
    """Get all task types with their default routing."""
    from app.services.llm.router import DEFAULT_ROUTING

    # Human-readable info for each task type
    task_type_info = {
        TaskType.THESIS_GENERATION: ("Thesis Generation", "Generate new investment thesis"),
        TaskType.THESIS_UPDATE: ("Thesis Update", "Update existing thesis with new data"),
        TaskType.NEWS_ANALYSIS: ("News Analysis", "Analyze news impact on stock"),
        TaskType.ASSUMPTION_GENERATION: ("Assumption Generation", "Generate financial assumptions"),
        TaskType.COMPANY_COMPARISON: ("Company Comparison", "Compare multiple companies"),
        TaskType.NOTE_EXTRACTION: ("Note Extraction", "Extract insights from analyst notes"),
        TaskType.WATCH_ITEMS: ("Watch Items", "Generate catalyst watch items"),
        TaskType.QUICK_SUMMARY: ("Quick Summary", "Generate short summaries"),
        TaskType.DATA_FORMATTING: ("Data Formatting", "Format structured output"),
    }

    result = []
    for task_type, (default_provider, default_model) in DEFAULT_ROUTING.items():
        info = task_type_info.get(task_type, (task_type.value, ""))
        result.append(TaskTypeInfo(
            type=task_type.value,
            name=info[0],
            description=info[1],
            default_provider=default_provider,
            default_model=default_model,
        ))

    return result


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

    # Log received update data (without sensitive values)
    logger.info(f"Updating settings for user {current_user.id}")
    logger.info(f"Fields received: {list(update_dict.keys())}")
    if 'finnhub_api_key' in update_dict:
        api_key = update_dict['finnhub_api_key']
        logger.info(f"finnhub_api_key provided: {bool(api_key) and len(api_key) > 0}")

    for key, value in update_dict.items():
        logger.debug(f"Setting {key} = {value if 'key' not in key else '***'}")
        setattr(settings, key, value)

    db.add(settings)
    await db.commit()
    await db.refresh(settings)

    logger.info(f"Settings updated successfully for user {current_user.id}")
    return settings


@router.put("/llm-route/{task_type}", response_model=dict)
async def update_llm_route(
    task_type: str,
    route_data: ModelRoute,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update the LLM route for a specific task type.

    Args:
        task_type: The task type to update (e.g., 'thesis_generation')
        route_data: Provider and model to use for this task
    """
    settings = current_user.settings

    # Initialize routing preferences if not set
    if settings.llm_routing_preferences is None:
        settings.llm_routing_preferences = {}

    # Update the route for this task type
    settings.llm_routing_preferences[task_type] = {
        "provider": route_data.provider,
        "model": route_data.model,
    }

    db.add(settings)
    await db.commit()
    await db.refresh(settings)

    logger.info(f"Updated LLM route for {task_type} to {route_data.provider}/{route_data.model}")
    return {"success": True, "task_type": task_type, "route": route_data.model_dump()}


@router.post("/llm-route/reset", response_model=dict)
async def reset_llm_routes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reset all LLM routes to defaults."""
    settings = current_user.settings
    settings.llm_routing_preferences = None

    db.add(settings)
    await db.commit()
    await db.refresh(settings)

    logger.info("Reset all LLM routes to defaults")
    return {"success": True, "message": "Routes reset to defaults"}
