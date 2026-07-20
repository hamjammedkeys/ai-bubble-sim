from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.chat.agent import run_chat
from app.db import get_session
from app.schemas import ChatIn, ChatOut

router = APIRouter()


@router.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn, session: Session = Depends(get_session)):
    result = run_chat([m.model_dump() for m in payload.messages], session)
    return ChatOut(reply=result["reply"], actions=result["actions"])
