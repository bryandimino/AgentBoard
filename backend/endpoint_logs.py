"""
Agent Board - Execution Log Endpoints

Log retrieval for card activity tracking.
"""

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from datetime import datetime

from models import ExecutionLog, engine


router = APIRouter()


def get_db_session():
    with Session(engine) as session:
        yield session


@router.get("/card/{card_id}")
async def get_card_logs(
    card_id: int,
    limit: int = 50,
    session: Session = Depends(get_db_session)
):
    """Get execution logs for a specific card."""
    # Verify card exists
    from models import Card
    card = session.get(Card, card_id)
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Get logs
    logs = session.exec(
        select(ExecutionLog)
        .where(ExecutionLog.card_id == card_id)
        .order_by(ExecutionLog.created_at.desc())
        .limit(limit)
    ).all()
    
    return {
        "card_id": card_id,
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "message": log.message,
                "context": log.context,
                "created_at": log.created_at.isoformat(),
                "user_id": log.user_id
            }
            for log in logs
        ],
        "total": len(logs)
    }


@router.post("/card/{card_id}/add")
async def add_log_entry(
    card_id: int,
    request,
    session: Session = Depends(get_db_session)
):
    """Add log entry for a card."""
    # Verify card exists
    from models import Card
    card = session.get(Card, card_id)
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    data = await request.json()
    
    log_entry = ExecutionLog(
        card_id=card_id,
        action=data.get("action", "manual_update"),
        message=data["message"],
        context=data.get("context"),
        user_id=data.get("user_id")
    )
    
    session.add(log_entry)
    session.commit()
    session.refresh(log_entry)
    
    return {
        "id": log_entry.id,
        "action": log_entry.action,
        "message": log_entry.message,
        "created_at": log_entry.created_at.isoformat()
    }


@router.get("/card/{card_id}/stats")
async def get_card_stats(
    card_id: int,
    session: Session = Depends(get_db_session)
):
    """Get activity statistics for a card."""
    from models import Card
    
    card = session.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Count logs by action type
    all_logs = session.exec(
        select(ExecutionLog).where(ExecutionLog.card_id == card_id)
    ).all()
    
    action_counts = {}
    for log in all_logs:
        action_counts[log.action] = action_counts.get(log.action, 0) + 1
    
    # Calculate duration if started
    from datetime import datetime as dt
    duration_seconds = None
    if card.started_at and (card.completed_at or True):  # Calculate to now if not completed
        end_time = card.completed_at or dt.now()
        duration_seconds = (end_time - card.started_at).total_seconds()
    
    return {
        "card_id": card_id,
        "title": card.title,
        "status": card.status.value if hasattr(card.status, 'value') else card.status,
        "logs_count": len(all_logs),
        "action_breakdown": action_counts,
        "duration_seconds": duration_seconds
    }
