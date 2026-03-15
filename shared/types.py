"""Shared type definitions for agent-board."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class CardType(str, Enum):
    """Type of work represented by a card."""
    TASK = "task"
    FEATURE = "feature"
    BUG = "bug"
    INVESTIGATION = "investigation"


class CardStatus(str, Enum):
    """Kanban board status for cards."""
    BACKLOG = "BACKLOG"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    DONE = "DONE"


class Priority(int, Enum):
    """Card priority levels."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class Card:
    """Kanban board card representing a unit of work."""
    
    id: Optional[int] = None
    title: str = ""
    type: str = "task"
    owner: Optional[str] = None
    role: Optional[str] = None
    priority: int = 1
    status: str = "BACKLOG"
    acceptance_criteria: Optional[str] = None
    dependencies: List[int] = None
    next_step: Optional[str] = None
    blockers: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class ExecutionLogEntry:
    """Activity log entry for card execution."""
    
    id: Optional[int] = None
    card_id: int = 0
    action: str = ""
    message: str = ""
    context: Optional[str] = None
    created_at: Optional[datetime] = None
    user_id: Optional[str] = None


@dataclass
class ActiveRun:
    """Track current agent execution for a card."""
    
    id: Optional[int] = None
    card_id: int = 0
    session_id: str = ""
    started_at: Optional[datetime] = None
    status: str = "running"
    outcome: Optional[str] = None
    evidence: Optional[str] = None
