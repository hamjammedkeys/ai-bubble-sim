from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Document, Edge, Passage
from app.schemas import EdgeDetailOut, EditEdgeIn, EdgeOut, ReviewIn
from app.services.review import InvalidTransition, approve_edge, edit_edge, reject_edge

router = APIRouter()


@router.get("/edges", response_model=list[EdgeOut])
def list_edges(status: str | None = None, session: Session = Depends(get_session)):
    query = session.query(Edge)
    if status is not None:
        query = query.filter(Edge.status == status)
    return query.order_by(Edge.created_at.desc()).all()


@router.get("/edges/candidates", response_model=list[EdgeOut])
def list_candidates(session: Session = Depends(get_session)):
    return (
        session.query(Edge)
        .filter(Edge.status == "candidate")
        .order_by(Edge.created_at.desc())
        .all()
    )


@router.get("/edges/{edge_id}", response_model=EdgeDetailOut)
def get_edge(edge_id: str, session: Session = Depends(get_session)):
    edge = session.get(Edge, edge_id)
    if edge is None:
        raise HTTPException(status_code=404, detail="edge not found")
    passage = session.get(Passage, edge.passage_id) if edge.passage_id else None
    document = session.get(Document, edge.document_id) if edge.document_id else None
    detail = EdgeDetailOut.model_validate(edge)
    detail.passage_text = passage.text if passage else None
    detail.document_title = document.title if document else None
    detail.document_url = document.url if document else None
    return detail


def _apply(action, session, edge_id, **kwargs) -> Edge:
    try:
        return action(session, edge_id, **kwargs)
    except KeyError:
        raise HTTPException(status_code=404, detail="edge not found")
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/edges/{edge_id}/approve", response_model=EdgeOut)
def approve(edge_id: str, payload: ReviewIn, session: Session = Depends(get_session)):
    return _apply(approve_edge, session, edge_id, reviewed_by=payload.reviewed_by)


@router.post("/edges/{edge_id}/reject", response_model=EdgeOut)
def reject(edge_id: str, payload: ReviewIn, session: Session = Depends(get_session)):
    return _apply(reject_edge, session, edge_id, reviewed_by=payload.reviewed_by)


@router.post("/edges/{edge_id}/edit", response_model=EdgeOut)
def edit(edge_id: str, payload: EditEdgeIn, session: Session = Depends(get_session)):
    updates = payload.model_dump(exclude_unset=True)
    try:
        return edit_edge(session, edge_id, updates)
    except KeyError:
        raise HTTPException(status_code=404, detail="edge not found")
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
