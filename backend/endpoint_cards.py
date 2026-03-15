"""
Agent Board - Card CRUD Endpoints

Full RESTful API for card operations:
  - GET /cards/list - List all cards
  - GET /cards/{id} - Get single card
  - POST /cards/create - Create new card
  - PUT /cards/{id} - Update card
  - DELETE /cards/{id} - Delete card
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select
from datetime import datetime
import json

from models import Card, BoardColumn, ExecutionLog, ActiveRun, CardStatus, CardType, engine


router = APIRouter()


def get_db_session():
    with Session(engine) as session:
        yield session


@router.get("/list")
async def list_cards(session: Session = Depends(get_db_session)):
    """List all cards."""
    cards = session.exec(select(Card).order_by(Card.created_at.desc())).all()
    
    return {
        "cards": [card_to_dict(c) for c in cards],
        "total": len(cards)
    }


@router.get("/{card_id}")
async def get_card(card_id: int, session: Session = Depends(get_db_session)):
    """Get single card by ID."""
    card = session.get(Card, card_id)
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    return card_to_dict(card)


@router.post("/create")
async def create_card(
    request: Request,
    session: Session = Depends(get_db_session)
):
    """Create new card."""
    data = await request.json()
    
    # Validate required fields
    if not data.get("title"):
        raise HTTPException(status_code=400, detail="Title is required")
    
    # Parse optional fields
    title = data["title"]
    card_type = CardType(data.get("type", "task"))
    priority = int(data.get("priority", 1))
    owner = data.get("owner")
    role = data.get("role")
    acceptance_criteria = data.get("acceptance_criteria")
    
    # Create card
    card = Card(
        title=title,
        type=card_type,
        priority=priority,
        owner=owner,
        role=role,
        acceptance_criteria=acceptance_criteria,
        dependencies=data.get("dependencies", "[]"),
        next_step=None,
        blockers=None,
        status=CardStatus.BACKLOG
    )
    
    session.add(card)
    session.commit()
    session.refresh(card)
    
    # Log creation event
    log_entry = ExecutionLog(
        card_id=card.id,
        action="created",
        message=f"Card created: {title}"
    )
    session.add(log_entry)
    session.commit()
    
    return card_to_dict(card)


@router.put("/{card_id}")
async def update_card(
    card_id: int,
    request: Request,
    session: Session = Depends(get_db_session)
):
    """Update existing card."""
    # Get existing card
    card = session.get(Card, card_id)
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    data = await request.json()
    
    # Update fields
    if "title" in data:
        card.title = data["title"]
    if "type" in data:
        card.type = CardType(data["type"])
    if "priority" in data:
        card.priority = int(data["priority"])
    if "owner" in data:
        card.owner = data["owner"]
    if "role" in data:
        card.role = data["role"]
    if "acceptance_criteria" in data:
        card.acceptance_criteria = data["acceptance_criteria"]
    if "dependencies" in data:
        card.dependencies = json.dumps(data["dependencies"])
    if "next_step" in data:
        card.next_step = data["next_step"]
    if "blockers" in data:
        card.blockers = data["blockers"]
    
    # Handle status transitions
    if "status" in data:
        old_status = card.status
        
        new_status = CardStatus(data["status"])
        
        # Update timestamps based on transition
        if new_status == CardStatus.IN_PROGRESS and old_status != CardStatus.IN_PROGRESS:
            card.started_at = datetime.now()
        elif new_status == CardStatus.DONE:
            card.completed_at = datetime.now()
        
        card.status = new_status
    
    card.updated_at = datetime.now()
    
    session.add(card)
    session.commit()
    session.refresh(card)
    
    # Log update event
    log_entry = ExecutionLog(
        card_id=card.id,
        action="updated",
        message=f"Card updated - status changed from {old_status} to {card.status}"
    )
    session.add(log_entry)
    session.commit()
    
    return card_to_dict(card)


@router.delete("/{card_id}")
async def delete_card(
    card_id: int,
    session: Session = Depends(get_db_session)
):
    """Delete card."""
    card = session.get(Card, card_id)
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Check if card has active run
    active_run = session.exec(
        select(ActiveRun).where(ActiveRun.card_id == card_id)
    ).first()
    
    if active_run and active_run.status == "running":
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete card with running agent"
        )
    
    session.delete(card)
    session.commit()
    
    return {"message": f"Card {card_id} deleted successfully"}


# Helper functions
def card_to_dict(card: Card) -> dict:
    """Convert Card object to dictionary."""
    return {
        "id": card.id,
        "title": card.title,
        "type": card.type.value if isinstance(card.type, CardType) else card.type,
        "priority": card.priority,
        "owner": card.owner,
        "role": card.role,
        "status": card.status.value if isinstance(card.status, CardStatus) else card.status,
        "acceptance_criteria": card.acceptance_criteria,
        "dependencies": json.loads(card.dependencies),
        "next_step": card.next_step,
        "blockers": card.blockers,
        "created_at": card.created_at.isoformat(),
        "updated_at": card.updated_at.isoformat(),
        "started_at": card.started_at.isoformat() if card.started_at else None,
        "completed_at": card.completed_at.isoformat() if card.completed_at else None,
    }

