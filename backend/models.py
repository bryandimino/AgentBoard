"""SQLModel database schemas for agent-board."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlmodel import Field, SQLModel


class Card(SQLModel, table=True):
    """Kanban board card representing a unit of work."""
    
    __tablename__ = "cards"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Core identity
    title: str = Field(..., min_length=1, max_length=200, index=True)
    type: str = Field(default="task", index=True)  # task | feature | bug | investigation
    
    # Ownership & assignment
    owner: Optional[str] = Field(default=None, max_length=100)
    role: Optional[str] = Field(default=None, max_length=100)
    
    # Prioritization
    priority: int = Field(default=1, ge=0, le=3)  # 0=critical, 1=high, 2=medium, 3=low
    
    # Status tracking
    status: str = Field(default="BACKLOG", index=True)  # BACKLOG | READY | IN_PROGRESS | BLOCKED | REVIEW | DONE
    
    # Work definition
    acceptance_criteria: Optional[str] = Field(default=None)
    dependencies: str = Field(default="[]", max_length=1000)  # JSON array of card IDs
    
    # Execution metadata
    next_step: Optional[str] = Field(default=None, max_length=500)
    blockers: Optional[str] = Field(default=None, max_length=1000)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now, index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    board_id: int = Field(default=1, index=True)  # Multi-board support future-proofing


class ExecutionLog(SQLModel, table=True):
    """Activity log for card execution."""
    
    __tablename__ = "executionlogs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: int = Field(foreign_key="cards.id", index=True)
    
    # Log content
    action: str = Field(..., max_length=50, index=True)
    
    # Human-readable description
    message: str = Field(..., min_length=1, max_length=2000)
    
    # Context as JSON string
    context: Optional[str] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    user_id: Optional[str] = Field(default=None, max_length=100)


class ActiveRun(SQLModel, table=True):
    """Track current agent execution for a card."""
    
    __tablename__ = "activeruns"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: int = Field(foreign_key="cards.id", unique=True, index=True)
    
    # Execution details
    session_id: str = Field(..., max_length=200)
    started_at: datetime = Field(default_factory=datetime.now, index=True)
    status: str = Field(default="running", max_length=50)
    
    # Results
    outcome: Optional[str] = Field(default=None, max_length=1000)
    evidence: Optional[str] = Field(default=None, max_length=500)
