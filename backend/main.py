"""FastAPI application for agent-board."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, create_engine, Session, select

import os

# Import all models first to register their tables
from models import Card, ExecutionLog, ActiveRun
import crud


# Database setup - ensure engine is created before lifespan context
DATABASE_URL = "sqlite:///../data/board.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization."""
    
    # Only create tables if database doesn't exist yet (preserve existing data)
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        SQLModel.metadata.create_all(engine)
        print("✅ Database initialized")
    else:
        print("📁 Database already exists - preserving data")
    
    print("✅ Database initialized")
    yield
    
    print("🔚 Application shutting down")


# App initialization
app = FastAPI(
    title="Agent Board API",
    description="Kanban-style orchestration system for managing agent work",
    version="0.1.0",
    lifespan=lifespan
)

# Mount static files for frontend - serve from frontend/static/ not frontend/
frontend_static_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "static")
if os.path.exists(frontend_static_path):
    print(f"✅ Mounting static files from {frontend_static_path} to /static")
    app.mount("/static", StaticFiles(directory=frontend_static_path), name="static")
else:
    print(f"❌ Static files not found at {frontend_static_path}")


# Pydantic models for request/response validation
class CardCreate(BaseModel):
    """Request model for creating a card."""
    title: str = Field(..., min_length=1, max_length=200)
    type: str = "task"
    owner: Optional[str] = None
    role: Optional[str] = None
    priority: int = Field(default=1, ge=0, le=3)
    status: str = "BACKLOG"
    acceptance_criteria: Optional[str] = None
    dependencies: str = "[]"  # JSON array as string to match DB model
    next_step: Optional[str] = None
    blockers: Optional[str] = None


class CardUpdate(BaseModel):
    """Request model for updating a card."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    type: Optional[str] = None
    owner: Optional[str] = None
    role: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=0, le=3)
    status: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    dependencies: Optional[List[int]] = None
    next_step: Optional[str] = None
    blockers: Optional[str] = None


class ExecutionLogCreate(BaseModel):
    """Request model for creating an execution log."""
    card_id: int
    action: str
    message: str
    context: Optional[str] = None
    user_id: Optional[str] = None


# Serve frontend at root
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the Agent Board frontend."""
    # Try static directory first, then parent directory (for index.html location compatibility)
    candidates = [
        os.path.join(frontend_static_path, "index.html"),  # /frontend/static/index.html
        os.path.join(os.path.dirname(frontend_static_path), "index.html")  # /frontend/index.html
    ]
    
    for index_file in candidates:
        if os.path.exists(index_file):
            with open(index_file, "r") as f:
                return HTMLResponse(content=f.read())
    
    return HTMLResponse(content="<h1>Agent Board</h1><p>Frontend not found.</p>")


# API Endpoints

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        with Session(engine) as session:
            # Test DB connectivity
            cards = crud.get_all_cards(session)
            return {
                "status": "healthy",
                "total_cards": len(cards),
                "database": "connected"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cards", response_model=List[crud.CardResponse])
async def get_all_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get all cards ordered by priority and created_at."""
    with Session(engine) as session:
        return crud.get_all_cards(session)


@app.post("/api/cards", response_model=crud.CardResponse)
async def create_card(card_data: CardCreate):
    """Create a new card."""
    with Session(engine) as session:
        card = crud.create_card(session, card_data.model_dump())
        return card


@app.get("/api/cards/{card_id}", response_model=Optional[crud.CardResponse])
async def get_card(card_id: int):
    """Get a single card by ID."""
    with Session(engine) as session:
        return crud.get_card_by_id(session, card_id)


@app.patch("/api/cards/{card_id}", response_model=Optional[crud.CardResponse])
async def update_card(card_id: int, card_data: CardUpdate):
    """Update an existing card."""
    with Session(engine) as session:
        updated = crud.update_card(session, card_id, card_data.model_dump(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Card not found")
        return updated


@app.delete("/api/cards/{card_id}", response_model=bool)
async def delete_card(card_id: int):
    """Delete a card by ID."""
    with Session(engine) as session:
        success = crud.delete_card(session, card_id)
        if not success:
            raise HTTPException(status_code=404, detail="Card not found")
        return success


@app.get("/api/cards/{card_id}/logs", response_model=List[crud.LogEntryResponse])
async def get_card_logs(card_id: int):
    """Get execution logs for a specific card."""
    with Session(engine) as session:
        return crud.get_execution_logs(session, card_id)


@app.get("/api/supervisor/ready-cards", response_model=List[crud.CardResponse])
async def get_ready_cards():
    """Get all cards in READY status for the supervisor to pick up."""
    with Session(engine) as session:
        return crud.get_cards_by_status(session, "READY")


@app.get("/api/supervisor/in-progress-cards", response_model=List[crud.CardResponse])
async def get_in_progress_cards():
    """Get all cards currently IN_PROGRESS (for supervisor WIP monitoring)."""
    with Session(engine) as session:
        return crud.get_cards_by_status(session, "IN_PROGRESS")


@app.post("/api/logs", response_model=crud.LogEntryResponse)
async def create_log_entry(log_data: ExecutionLogCreate):
    """Create a new execution log entry."""
    with Session(engine) as session:
        return crud.create_execution_log(session, log_data.model_dump())


# Supervisor endpoints - for agent orchestration

@app.get("/api/supervisor/active-runs", response_model=List[crud.ActiveRunResponse])
async def get_active_runs():
    """Get all active agent runs."""
    with Session(engine) as session:
        return crud.get_all_active_runs(session)


@app.post("/api/supervisor/active-runs", response_model=crud.ActiveRunResponse)
async def start_new_run(run_data: dict):
    """Start a new supervisor run for a specific card."""
    # Note: run_data should include card_id, session_id, and optionally outcome/evidence
    with Session(engine) as session:
        run = crud.start_active_run(
            session,
            card_id=run_data.get("card_id"),
            session_id=run_data.get("session_id", "default")
        )
        return run


@app.patch("/api/supervisor/active-runs/{run_id}/status", response_model=Optional[crud.ActiveRunResponse])
async def update_run_status(run_id: int, status: str):
    """Update the status of an active run."""
    with Session(engine) as session:
        updated = crud.update_active_run_status(session, run_id, status)
        if not updated:
            raise HTTPException(status_code=404, detail="Active run not found")
        return updated


@app.post("/api/supervisor/active-runs/{run_id}/close", response_model=Optional[crud.ActiveRunResponse])
async def close_run(run_id: int):
    """Close an active run after task completion."""
    with Session(engine) as session:
        closed = crud.close_active_run(session, run_id)
        if not closed:
            raise HTTPException(status_code=404, detail="Active run not found")
        return closed


# Board statistics

@app.get("/api/stats")
async def get_board_stats():
    """Get board statistics for frontend display."""
    with Session(engine) as session:
        total = crud.count_all_cards(session)
        ready = crud.count_cards_by_status(session, "READY")
        in_progress = crud.count_cards_by_status(session, "IN_PROGRESS")
        done = crud.count_cards_by_status(session, "DONE")
        return {
            "total": total,
            "ready": ready,
            "in_progress": in_progress,
            "done": done
        }
