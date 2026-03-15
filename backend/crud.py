"""CRUD operations for agent-board database."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from models import Card, ExecutionLog, ActiveRun


# Pydantic response models for API responses
class CardResponse(BaseModel):
    """Pydantic model for card API responses."""
    id: int
    title: str
    type: str
    owner: Optional[str] = None
    role: Optional[str] = None
    priority: int
    status: str
    acceptance_criteria: Optional[str] = None
    dependencies: str
    next_step: Optional[str] = None
    blockers: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    board_id: int
    
    class Config:
        from_attributes = True


class LogEntryResponse(BaseModel):
    """Pydantic model for execution log API responses."""
    id: int
    card_id: int
    action: str
    message: str
    context: Optional[str] = None
    created_at: datetime
    user_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class ActiveRunResponse(BaseModel):
    """Pydantic model for active run API responses."""
    id: int
    card_id: int
    session_id: str
    started_at: datetime
    status: str
    outcome: Optional[str] = None
    evidence: Optional[str] = None
    
    class Config:
        from_attributes = True


class BoardStats(BaseModel):
    """Pydantic model for board statistics."""
    total_cards: int
    cards_by_status: dict
    cards_by_priority: dict
    active_runs: int
    completed_today: int
    
    class Config:
        from_attributes = True


# CRUD operations

def get_all_cards(session: Session) -> List[CardResponse]:
    """Get all cards ordered by priority and created_at."""
    statement = select(Card).order_by(Card.priority, Card.created_at)
    results = session.exec(statement).all()
    return [CardResponse.model_validate(card) for card in results]


def get_card_by_id(session: Session, card_id: int) -> Optional[CardResponse]:
    """Get a single card by ID."""
    card = session.get(Card, card_id)
    if not card:
        return None
    return CardResponse.model_validate(card)


def create_card(session: Session, card_data: dict) -> CardResponse:
    """Create a new card."""
    card = Card(**card_data)
    session.add(card)
    session.commit()
    session.refresh(card)
    return CardResponse.model_validate(card)


def update_card(session: Session, card_id: int, card_data: dict) -> Optional[CardResponse]:
    """Update an existing card."""
    card = session.get(Card, card_id)
    if not card:
        return None
    
    for field, value in card_data.items():
        if hasattr(card, field):
            setattr(card, field, value)
    
    # Update timestamp properly using datetime.now()
    from models import datetime as dt
    card.updated_at = dt.now()
    
    session.add(card)
    session.commit()
    session.refresh(card)
    return CardResponse.model_validate(card)


def delete_card(session: Session, card_id: int) -> bool:
    """Delete a card by ID."""
    card = session.get(Card, card_id)
    if not card:
        return False
    
    session.delete(card)
    session.commit()
    return True


def get_cards_by_status(session: Session, status: str) -> List[CardResponse]:
    """Get cards filtered by status."""
    statement = select(Card).where(Card.status == status).order_by(Card.priority, Card.created_at)
    results = session.exec(statement).all()
    return [CardResponse.model_validate(card) for card in results]


def get_ready_cards(session: Session, limit: int = 10) -> List[CardResponse]:
    """Get READY cards sorted by priority and created_at."""
    statement = select(Card).where(Card.status == "READY").order_by(Card.priority, Card.created_at).limit(limit)
    results = session.exec(statement).all()
    return [CardResponse.model_validate(card) for card in results]


def get_in_progress_cards(session: Session) -> List[CardResponse]:
    """Get all IN_PROGRESS cards."""
    statement = select(Card).where(Card.status == "IN_PROGRESS")
    results = session.exec(statement).all()
    return [CardResponse.model_validate(card) for card in results]


def get_blocked_cards(session: Session) -> List[CardResponse]:
    """Get all BLOCKED cards."""
    statement = select(Card).where(Card.status == "BLOCKED").order_by(Card.updated_at.desc())
    results = session.exec(statement).all()
    return [CardResponse.model_validate(card) for card in results]


def get_execution_logs(session: Session, card_id: int) -> List[LogEntryResponse]:
    """Get execution logs for a specific card."""
    statement = select(ExecutionLog).where(ExecutionLog.card_id == card_id).order_by(ExecutionLog.created_at.desc())
    results = session.exec(statement).all()
    return [LogEntryResponse.model_validate(log) for log in results]


def create_execution_log(session: Session, log_data: dict) -> LogEntryResponse:
    """Create a new execution log entry."""
    log_entry = ExecutionLog(**log_data)
    session.add(log_entry)
    session.commit()
    session.refresh(log_entry)
    return LogEntryResponse.model_validate(log_entry)


def get_active_run_for_card(session: Session, card_id: int) -> Optional[ActiveRun]:
    """Get active run for a specific card."""
    statement = select(ActiveRun).where(ActiveRun.card_id == card_id)
    return session.exec(statement).first()


def start_active_run(session: Session, card_id: int, session_id: str) -> ActiveRun:
    """Create a new active run record."""
    # Check if there's already an active run for this card
    existing = get_active_run_for_card(session, card_id)
    if existing:
        return existing
    
    run = ActiveRun(card_id=card_id, session_id=session_id)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def update_active_run_status(session: Session, run_id: int, status: str) -> Optional[ActiveRunResponse]:
    """Update the status of an active run."""
    run = session.get(ActiveRun, run_id)
    if not run:
        return None
    
    run.status = status
    session.add(run)
    session.commit()
    session.refresh(run)
    return ActiveRunResponse.model_validate(run)


def close_active_run(session: Session, run_id: int) -> Optional[ActiveRunResponse]:
    """Delete the active run record when work is complete."""
    run = session.get(ActiveRun, run_id)
    if not run:
        return None
    
    session.delete(run)
    session.commit()
    return ActiveRunResponse.model_validate(run)


def get_all_active_runs(session: Session) -> List[ActiveRunResponse]:
    """Get all active agent runs."""
    statement = select(ActiveRun).where(ActiveRun.status == "running")
    results = session.exec(statement).all()
    return [ActiveRunResponse.model_validate(run) for run in results]


def get_board_stats(session: Session) -> dict:
    """Get board statistics."""
    # Count cards by status
    all_cards = session.exec(select(Card)).all()
    cards_by_status = {
        "BACKLOG": 0, "READY": 0, "IN_PROGRESS": 0, 
        "BLOCKED": 0, "REVIEW": 0, "DONE": 0
    }
    cards_by_priority = {0: 0, 1: 0, 2: 0, 3: 0}
    
    for card in all_cards:
        cards_by_status[card.status] = cards_by_status.get(card.status, 0) + 1
        cards_by_priority[card.priority] = cards_by_priority.get(card.priority, 0) + 1
    
    # Count active runs
    active_runs = session.exec(select(ActiveRun).where(ActiveRun.status == "running")).all()
    
    return {
        "total_cards": len(all_cards),
        "cards_by_status": cards_by_status,
        "cards_by_priority": cards_by_priority,
        "active_runs": len(active_runs),
        "completed_today": sum(1 for c in all_cards if c.completed_at and datetime.now().date() == c.completed_at.date())
    }


def count_all_cards(session: Session) -> int:
    """Count all cards in the database."""
    statement = select(Card)
    results = session.exec(statement).all()
    return len(results)


def count_cards_by_status(session: Session, status: str) -> int:
    """Count cards by status."""
    statement = select(Card).where(Card.status == status)
    results = session.exec(statement).all()
    return len(results)

