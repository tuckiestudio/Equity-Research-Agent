"""Notes API endpoints — manage analyst notes and AI extraction."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.note import Note
from app.models.stock import Stock
from app.models.user import User
from app.schemas.note import ExtractionResult, NoteCreate, NoteResponse, NoteUpdate
from app.services.llm.prompts.templates import get_note_extraction_template
from app.services.llm.router import LLMRouter
from app.services.llm.types import TaskType

router = APIRouter(prefix="/notes", tags=["notes"])


async def get_stock_by_ticker(ticker: str, db: AsyncSession, user: User) -> Stock:
    """Get a stock by ticker, raising NotFoundError if missing."""
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)
    return stock


async def get_note_by_id(note_id: str, db: AsyncSession, user: User) -> Note:
    """Get note by ID, ensuring it belongs to the user."""
    try:
        note_uuid = uuid.UUID(note_id)
    except ValueError:
        raise NotFoundError("Note", note_id)

    result = await db.execute(
        select(Note).where(
            Note.id == note_uuid,
            Note.user_id == user.id,
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise NotFoundError("Note", note_id)
    return note


def db_to_response(note: Note) -> NoteResponse:
    """Convert database model to response schema."""
    return NoteResponse(
        id=str(note.id),
        stock_id=str(note.stock_id),
        user_id=str(note.user_id),
        title=note.title,
        content=note.content,
        note_type=note.note_type,
        tags=note.get_tags(),
        extracted_sentiment=note.extracted_sentiment,
        extracted_key_points=note.get_extracted_key_points(),
        extracted_price_target=note.extracted_price_target,
        extracted_metrics=note.get_extracted_metrics(),
        is_ai_processed=note.is_ai_processed,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.post("/{ticker}", response_model=NoteResponse)
async def create_note(
    ticker: str,
    note_data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    """Create a new note for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    note = Note(
        stock_id=stock.id,
        user_id=current_user.id,
        title=note_data.title,
        content=note_data.content,
        note_type=note_data.note_type,
    )
    note.set_tags(note_data.tags)

    db.add(note)
    await db.commit()
    await db.refresh(note)

    return db_to_response(note)


@router.get("/{ticker}", response_model=list[NoteResponse])
async def list_notes(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NoteResponse]:
    """List notes for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    result = await db.execute(
        select(Note)
        .where(
            Note.stock_id == stock.id,
            Note.user_id == current_user.id,
        )
        .order_by(Note.created_at.desc())
    )
    notes = result.scalars().all()

    return [db_to_response(note) for note in notes]


@router.get("/detail/{note_id}", response_model=NoteResponse)
async def get_note_detail(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    """Get a single note by ID."""
    note = await get_note_by_id(note_id, db, current_user)
    return db_to_response(note)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    update_data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse:
    """Update an existing note."""
    note = await get_note_by_id(note_id, db, current_user)

    if update_data.title is not None:
        note.title = update_data.title
    if update_data.content is not None:
        note.content = update_data.content
    if update_data.note_type is not None:
        note.note_type = update_data.note_type
    if update_data.tags is not None:
        note.set_tags(update_data.tags)

    await db.commit()
    await db.refresh(note)

    return db_to_response(note)


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a note."""
    note = await get_note_by_id(note_id, db, current_user)

    await db.delete(note)
    await db.commit()

    return {"message": f"Note '{note.title}' deleted successfully"}


@router.post("/{note_id}/extract", response_model=ExtractionResult)
async def extract_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionResult:
    """Run AI extraction on a note and persist results."""
    note = await get_note_by_id(note_id, db, current_user)

    template = get_note_extraction_template()
    messages = template.render(
        extraction_fields=["sentiment", "key_points", "price_target", "metrics"],
        note_text=note.content,
    )

    llm_router = LLMRouter()
    try:
        response = await llm_router.complete(
            task_type=TaskType.NOTE_EXTRACTION,
            messages=messages,
            json_mode=True,
        )
        extraction_payload = json.loads(response.content)
        extraction = ExtractionResult(
            sentiment=extraction_payload.get("sentiment"),
            key_points=extraction_payload.get("key_points", []),
            price_target=extraction_payload.get("price_target"),
            metrics=extraction_payload.get("metrics", {}),
        )
    except (json.JSONDecodeError, TypeError, ValueError):
        extraction = ExtractionResult(
            sentiment=None,
            key_points=[],
            price_target=None,
            metrics={},
        )
    except Exception:
        extraction = ExtractionResult(
            sentiment=None,
            key_points=[],
            price_target=None,
            metrics={},
        )

    note.extracted_sentiment = extraction.sentiment
    note.set_extracted_key_points(extraction.key_points)
    note.extracted_price_target = extraction.price_target
    note.set_extracted_metrics(extraction.metrics)
    note.is_ai_processed = True

    await db.commit()
    await db.refresh(note)

    return extraction
