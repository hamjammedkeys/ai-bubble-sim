from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.extraction.adapter import extract_document_candidates
from app.ingestion import fetch_url_text
from app.models import Document, Entity
from app.schemas import DocumentFromUrlIn, DocumentIn, DocumentOut, EntityOut, ExtractResponse
from app.services.candidates import persist_candidates

router = APIRouter()


@router.get("/entities", response_model=list[EntityOut])
def list_entities(session: Session = Depends(get_session)):
    return session.query(Entity).order_by(Entity.name).all()


@router.post("/documents", response_model=DocumentOut, status_code=201)
def create_document(payload: DocumentIn, session: Session = Depends(get_session)):
    document = Document(
        title=payload.title,
        raw_text=payload.raw_text,
        filing_type=payload.filing_type,
        company=payload.company,
        url=payload.url,
        period=payload.period,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.post("/documents/from_url", response_model=DocumentOut, status_code=201)
def create_document_from_url(payload: DocumentFromUrlIn, session: Session = Depends(get_session)):
    try:
        text = fetch_url_text(payload.url)
    except Exception as exc:  # network / reader failure
        raise HTTPException(status_code=502, detail=f"could not read {payload.url}: {exc}")
    if not text.strip():
        raise HTTPException(status_code=422, detail="the reader returned no text for that URL")
    document = Document(title=payload.title or payload.url, url=payload.url, raw_text=text)
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.post("/documents/{document_id}/extract", response_model=ExtractResponse)
def extract_document(
    document_id: str,
    provider: str | None = None,
    session: Session = Depends(get_session),
):
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")

    known_entities = [name for (name,) in session.query(Entity.name).all()]
    chosen_provider = provider or settings.llm_provider
    result = extract_document_candidates(
        document.raw_text,
        known_entities,
        document_id=document.id,
        provider=chosen_provider,
    )
    edges = persist_candidates(session, result, document)
    return ExtractResponse(
        document_id=document.id,
        candidates_created=len(edges),
        provider=chosen_provider,
    )
