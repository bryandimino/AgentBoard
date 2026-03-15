"""
Agent Board - Supervisor Loop Endpoint

Cron-executable supervisor logic that:
1. Inspects board state
2. Decides next action (continue existing or start new)
3. Spawns subagents via OpenClaw API
4. Updates card states and logs
"""

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
import json

from models import Card, ExecutionLog, ActiveRun, CardStatus, engine


router = APIRouter()


def get_db_session():
    with Session(engine) as session:
        yield session


@router.post("/run")
async def run_supervisor(
    request,
    session: Session = Depends(get_db_session)
):
    """
    Execute supervisor loop - decides next action for agent work.
    
    Decision logic (prioritized):
    1. Continue IN_PROGRESS card if exists
    2. Start new READY card (respecting WIP limit of 1)
    3. No actionable work
    
    Returns: Supervisor decision with details
    """
    
    # Get board state
    in_progress_cards = session.exec(
        select(Card).where(Card.status == CardStatus.IN_PROGRESS)
    ).all()
    
    ready_cards = session.exec(
        select(Card).where(Card.status == CardStatus.READY)
    ).order_by(Card.priority.asc(), Card.created_at.asc()).all()
    
    active_runs_count = len(session.exec(select(ActiveRun)).all())
    
    # Decision 1: Continue existing work
    if in_progress_cards:
        card = in_progress_cards[0]
        
        decision = {
            "action": "continue_existing",
            "card_id": card.id,
            "title": card.title,
            "reason": f"Continuing work on card #{card.id}",
            "priority": card.priority,
            "started_at": card.started_at.isoformat() if card.started_at else None
        }
        
        # Log decision
        log_entry = ExecutionLog(
            card_id=card.id,
            action="supervisor_inspect",
            message=f"Supervisor deciding to continue existing work: {card.title}"
        )
        session.add(log_entry)
        session.commit()
        
        return decision
    
    # Decision 2: Start new work (respect WIP limit)
    MAX_ACTIVE_RUNS = 1  # One card per agent at a time
    
    if ready_cards and active_runs_count < MAX_ACTIVE_RUNS:
        selected_card = ready_cards[0]
        
        # In production, would spawn subagent here via OpenClaw API
        decision = {
            "action": "start_new",
            "card_id": selected_card.id,
            "title": selected_card.title,
            "reason": f"Starting new work on card #{selected_card.id} ({get_priority_label(selected_card.priority)})",
            "priority": selected_card.priority,
            "owner": selected_card.owner,
            "role": selected_card.role,
            "acceptance_criteria": selected_card.acceptance_criteria
        }
        
        # Log decision
        log_entry = ExecutionLog(
            card_id=selected_card.id,
            action="supervisor_decision",
            message=f"Supervisor decided to start new work: {selected_card.title}"
        )
        session.add(log_entry)
        session.commit()
        
        return decision
    
    # Decision 3: No actionable work
    decision = {
        "action": "no_work",
        "reason": "No ready or in-progress cards within WIP limits",
        "in_progress_count": len(in_progress_cards),
        "ready_count": len(ready_cards),
        "active_runs": active_runs_count,
        "max_active_runs": MAX_ACTIVE_RUNS
    }
    
    return decision


def get_priority_label(priority: int) -> str:
    """Convert priority number to label."""
    labels = {
        0: "Critical",
        1: "High",
        2: "Medium-Low",
        3: "Low"
    }
    return labels.get(priority, f"Unknown ({priority})")


@router.get("/state")
async def get_supervisor_state(
    session: Session = Depends(get_db_session)
):
    """Get current board state summary for supervisor."""
    
    in_progress = session.exec(
        select(Card).where(Card.status == CardStatus.IN_PROGRESS)
    ).all()
    
    ready = session.exec(
        select(Card).where(Card.status == CardStatus.READY)
    ).count()
    
    backlog = session.exec(
        select(Card).where(Card.status == CardStatus.BACKLOG)
    ).count()
    
    done = session.exec(
        select(Card).where(Card.status == CardStatus.DONE)
    ).count()
    
    active_runs = len(session.exec(select(ActiveRun)).all())
    
    return {
        "total_cards": session.exec(select(Card)).count(),
        "by_status": {
            "BACKLOG": backlog,
            "READY": ready,
            "IN_PROGRESS": len(in_progress),
            "BLOCKED": session.exec(
                select(Card).where(Card.status == CardStatus.BLOCKED)
            ).count(),
            "REVIEW": session.exec(
                select(Card).where(Card.status == CardStatus.REVIEW)
            ).count(),
            "DONE": done
        },
        "active_runs": active_runs,
        "wip_limit": 1
    }
