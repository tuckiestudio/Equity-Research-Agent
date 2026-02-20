"""Export API endpoints."""
from __future__ import annotations

import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.scenarios import compute_weighted_summary
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.scenario import Scenario
from app.models.stock import Stock
from app.models.user import User
from app.services.model.comps import CompsEngine
from app.services.model.export import ModelExporter

router = APIRouter(prefix="/export", tags=["export"])


async def get_stock_by_ticker(
    ticker: str, db: AsyncSession, user: User
) -> Stock:
    """Get a stock by ticker, raising NotFoundError if missing."""
    result = await db.execute(
        select(Stock).where(Stock.ticker == ticker.upper())
    )
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)
    return stock


@router.get("/{ticker}/model")
async def export_model(
    ticker: str,
    peers: Optional[list[str]] = Query(
        default=None,
        description="Peer tickers (repeat query param to add multiple)",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Export comps and scenarios to an Excel file."""
    stock = await get_stock_by_ticker(ticker, db, current_user)
    peers_list = [peer.upper() for peer in peers] if peers else []

    result = await db.execute(
        select(Scenario).where(
            Scenario.stock_id == stock.id,
            Scenario.user_id == current_user.id,
        )
    )
    scenarios = result.scalars().all()
    summary = compute_weighted_summary(list(scenarios))

    comps_engine = CompsEngine()
    comps_result = await comps_engine.analyze(ticker, peers_list)

    exporter = ModelExporter()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_file_path = temp_file.name
    temp_file.close()

    exporter.export_to_excel(
        file_path=temp_file_path,
        comps=comps_result,
        scenarios=list(scenarios),
        weighted_target_price=summary.target_price,
    )

    filename = f"{stock.ticker.lower()}_model.xlsx"
    return FileResponse(
        temp_file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
