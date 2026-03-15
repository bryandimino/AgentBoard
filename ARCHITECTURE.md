# Agent Board - Technical Architecture

**Status**: MVP Phase — v0.1.0  
**Last Updated**: 2026-03-14  
**Author**: Quinn 3.5

---

## 🎯 System Overview

The Agent Board is a kanban-style orchestration system for managing agent work:
- **Board View**: Human-operable interface for task management
- **Task Cards**: Structured units of work with metadata
- **Agent Integration**: Subagent spawning and tracking via OpenClaw
- **Supervisor Loop**: Cron-driven automation that keeps work progressing
- **Persistent State**: SQLite database for reliable data storage

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    HUMAN OPERATOR                           │
│                     (OpenClaw Interface)                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
         ┌──────────────▼──────────────┐
         │    FRONTEND UI (v8002)     │
         │  - Kanban Board View       │
         │  - Card Creation/Edit      │
         │  - Status Transitions      │
         └──────────────┬──────────────┘
                        │ HTTP API calls
         ┌──────────────▼──────────────┐
         │   BACKEND API (v8001)       │
         │   FastAPI + SQLite          │
         │                             │
         │  ├── /api/board            │
         │  ├── /api/cards            │
         │  ├── /api/logs             │
         │  └── /api/supervisor       │
         └──────────────┬──────────────┘
                        │ SQLite queries
         ┌──────────────▼──────────────┐
         │     DATABASE (board.db)     │
         │                             │
         │  ├── cards                  │
         │  ├── board_columns          │
         │  ├── execution_logs         │
         │  └── active_runs            │
         └─────────────────────────────┘
                        │
         ┌──────────────▼──────────────┐
         │     SUPERVISOR LOOP         │
         │   (Cron-executed script)    │
         │                             │
         │  - Inspect board state      │
         │  - Spawn subagents          │
         │  - Update log entries       │
         └─────────────────────────────┘
                        │
         ┌──────────────▼──────────────┐
         │    OPENCRAW AGENT SYSTEM     │
         │   (sessions_spawn, etc.)     │
         └─────────────────────────────┘
```

---

## 📦 Technology Stack Decisions

### Backend: FastAPI + SQLite

**Why:**
- ✅ **FastAPI**: Modern Python framework, automatic OpenAPI docs, async support
- ✅ **SQLite**: Zero-config persistence, file-based (portable), ACID compliant
- ✅ **SQLModel**: Type-safe ORM with Pydantic validation
- ⚡ Fast development velocity
- 🔧 Simple deployment (single dependency: SQLite)

**Alternative Considered:** PostgreSQL  
**Rejected because:** MVP requires simplicity; SQLite is sufficient for single-user operation

### Frontend: Vanilla HTML/CSS/JS

**Why:**
- ✅ **No framework overhead**: Single files, easy to inspect and modify
- ✅ **Direct API communication**: No build step required
- ✅ **Transparent behavior**: What you see is what you execute
- ⚡ Instant updates when editing source files

**Alternative Considered:** React/Vue  
**Rejected because:** Over-engineering for MVP; vanilla JS provides full functionality with less complexity

### Persistence: SQLite + SQLModel

**Database Schema**:
```sql
-- Core entities
cards                -- Kanban cards
board_columns        -- Column definitions (BACKLOG, TODO, etc.)
execution_logs       -- Per-card activity log
active_runs          -- Current subagent execution state

-- Relationships
-- cards → board_columns (many-to-many for statuses)
-- cards → execution_logs (one-to-many)
-- cards → active_runs (one-to-one for in-progress work)
```

---

## 📊 Data Model

### Card Entity

```python
class Card(SQLModel, table=True):
    """Kanban board card representing a unit of work."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Core identity
    title: str = Field(..., min_length=1, max_length=200)
    type: str = Field(default="task")  # task | feature | bug | investigation
    
    # Ownership & assignment
    owner: Optional[str] = Field(default=None)  # Agent ID or human name
    role: Optional[str] = Field(default=None)   # Role in execution (coder, reviewer, etc.)
    
    # Prioritization
    priority: int = Field(default=1, ge=0, le=3)  # 0=critical, 1=high, 2=medium, 3=low
    
    # Status tracking
    status: str = Field(default="BACKLOG")  # BACKLOG | READY | IN_PROGRESS | BLOCKED | REVIEW | DONE
    
    # Work definition
    acceptance_criteria: Optional[str] = Field(default=None)  # Markdown text
    dependencies: list = Field(default_factory=list, alias="dependency_card_ids")  # Array of card IDs
    
    # Execution metadata
    next_step: Optional[str] = Field(default=None)  # What to do next
    blockers: Optional[str] = Field(default=None)   # What's blocking progress
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None  # When IN_PROGRESS began
    completed_at: Optional[datetime] = None  # When DONE set
    
    # Metadata
    board_id: Optional[int] = Field(default=1)  # Multi-board support future-proofing
    
    class Config:
        orm_mode = True
```

### Execution Log Entry

```python
class ExecutionLog(SQLModel, table=True):
    """Activity log for card execution."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: int = Field(..., foreign_key="cards.id")
    
    # Log content
    action: str  # created | updated | in_progress | spawned_subagent | completed | blocked
    
    # Human-readable description
    message: str = Field(..., min_length=1)
    
    # Context
    context: Optional[str] = Field(default=None)  # JSON metadata (e.g., subagent session ID)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = Field(default=None)  # Who triggered this
    
    class Config:
        orm_mode = True
```

### Active Run Tracking

```python
class ActiveRun(SQLModel, table=True):
    """Track current agent execution for a card."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: int = Field(..., unique=True, foreign_key="cards.id")
    
    # Execution details
    session_id: str  # OpenClaw session ID spawned for this work
    started_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(default="running")  # running | completed | failed
    
    # Results
    outcome: Optional[str] = Field(default=None)  # Success/failure summary
    evidence: Optional[str] = Field(default=None)  # File path to work output
    
    class Config:
        orm_mode = True
```

---

## 🔄 Card Lifecycle & Status Transitions

```
BACKLOG ──▶ READY ──▶ IN_PROGRESS ──▶ REVIEW ──▶ DONE
                 │              │
                 └── BLOCKED ◀────┘ (from any in-progress state)

Transitions:
- BACKLOG → READY: Card is complete, ready for execution
- READY → IN_PROGRESS: Agent assigned, work begins
- IN_PROGRESS → REVIEW: Work complete, needs validation
- REVIEW → DONE: Validated successfully
- REVIEW → IN_PROGRESS: Needs revision
- Any → BLOCKED: External blocker identified
- BLOCKED → READY/IN_PROGRESS: Unblock and continue
```

**Rules:**
1. Only ONE card per agent can be IN_PROGRESS at a time (WIP limit = 1)
2. Cards move to REVIEW when work is complete but not yet validated
3. Agents must update cards with `next_step` before transitioning status

---

## 🤖 Supervisor Loop Design

### Purpose
The supervisor loop is a cron-executable script that:
1. Inspects board state
2. Decides what work needs attention
3. Spawns subagents when justified
4. Updates card states and logs

### Decision Logic (Prioritized)

```python
def decide_next_action(board_state):
    """
    Returns decision for next action to take:
    - continue_existing: Assign existing IN_PROGRESS card
    - start_new: Spawn agent on READY card
    - no_work: All cards complete or blocked
    """
    
    # Priority 1: Continue in-progress work
    in_progress_cards = [c for c in board.cards if c.status == "IN_PROGRESS"]
    if in_progress_cards:
        return {
            "action": "continue_existing",
            "card_id": in_progress_cards[0].id,
            "reason": f"Continuing work on card #{in_progress_cards[0].id}"
        }
    
    # Priority 2: Start new READY card (respecting WIP limit)
    ready_cards = [c for c in board.cards if c.status == "READY"]
    if ready_cards and total_active_runs < MAX_ACTIVE_RUNS:
        # Sort by priority, then created_at
        ready_cards.sort(key=lambda x: (x.priority, x.created_at))
        selected = ready_cards[0]
        
        return {
            "action": "start_new",
            "card_id": selected.id,
            "reason": f"Starting new work on card #{selected.id} ({get_priority_label(selected.priority)})"
        }
    
    # Priority 3: No actionable work
    return {
        "action": "no_work",
        "reason": "No ready or in-progress cards within WIP limits"
    }
```

### Supervisor Execution Flow

```bash
1. Read board state from database
2. Count active runs (WIP limit check)
3. Check for IN_PROGRESS cards that need updates
4. If no in-progress cards:
   a. Find highest-priority READY card
   b. Spawn subagent session with OpenClaw
   c. Update card to IN_PROGRESS
   d. Log spawn event
5. Update active run status
6. Record supervisor decision in execution_logs
7. Exit (cron can trigger again)
```

**File:** `scripts/supervisor.sh` - Executable shell script for cron

---

## 🔌 Integration Points

### OpenClaw Agent Spawning

```python
# Pseudocode for subagent spawning
def spawn_subagent_for_card(card_id):
    """Spawn OpenClaw session for card execution."""
    
    # Read card details from database
    card = get_card(card_id)
    
    # Build context from card metadata
    context = {
        "card_title": card.title,
        "acceptance_criteria": card.acceptance_criteria,
        "dependencies": card.dependencies,
        "next_step": card.next_step
    }
    
    # Spawn session using OpenClaw API
    result = sessions_spawn(
        task=f"Execute work for card {card.id}: {card.title}",
        label=f"agent-{card.id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        mode="session",  # Persistent thread-bound session
        runtime="acp",   # ACP harness for coding tasks
        cwd="/DIMINOCLAW/agent-board",
        attachments=[
            {
                "name": f"card_{card.id}.md",
                "content": format_card_context(card),
                "mimeType": "text/markdown"
            }
        ]
    )
    
    # Track active run
    create_active_run(
        card_id=card.id,
        session_id=result.session_id,
        status="running"
    )
    
    return result
```

### Cron Integration

**Crontab entry:**
```bash
*/5 * * * * cd /DIMINOCLAW/agent-board && ./scripts/supervisor.sh >> logs/supervisor.log 2>&1
```

**Supervisor script must be idempotent:**
- Safe to run multiple times per minute
- Checks state before making changes
- Logs all decisions regardless of action taken

---

## 📁 Directory Structure (Final)

```
DIMINOCLAW/agent-board/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # SQLModel database schemas
│   ├── crud.py              # CRUD operations for each entity
│   ├── endpoints/
│   │   ├── board.py         # /api/board endpoints
│   │   ├── cards.py         # /api/cards endpoints
│   │   ├── logs.py          # /api/logs endpoints
│   │   └── supervisor.py    # /api/supervisor endpoints
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html           # Main HTML file (single-page app)
│   ├── css/
│   │   ├── board.css        # Core kanban board styles
│   │   └── cards.css        # Card-specific styling
│   ├── js/
│   │   ├── app.js           # Main application logic
│   │   ├── api.js           # API client functions
│   │   ├── board.js         # Board rendering & events
│   │   └── cards.js         # Card management & interactions
│   └── lib/                 # External libraries (if needed)
├── shared/
│   └── types.py             # Shared type definitions
├── scripts/
│   ├── supervisor.sh        # Cron-executable supervisor loop
│   └── start_backend.sh     # Helper to launch backend
│   └── start_frontend.sh    # Helper to serve frontend
├── logs/                    # Runtime logs (gitignored)
│   └── .gitkeep
├── data/
│   └── board.db             # SQLite database file
├── README.md
├── LIVING_PROGRESS_LOG.md
├── ARCHITECTURE.md          # This file
├── ROADMAP.md
├── .env.example
└── setup.sh                 # Bootstrap script
```

---

## 🔐 Security Considerations (MVP)

1. **No Authentication**: Designed for single-user local operation
2. **Supervisor Isolation**: Supervisor runs with project scope only
3. **File Permissions**: SQLite DB and logs have standard permissions
4. **Input Validation**: All API inputs validated via SQLModel/Pydantic
5. **No External Calls**: Backend doesn't call external APIs except OpenClaw

**Post-MVP Security:**
- Add user authentication (JWT)
- Role-based access control
- API rate limiting
- Audit logging for all state changes

---

## 🧪 Testing Strategy

### MVP Testing
- Manual testing via browser UI
- API testing with Swagger docs (`/docs`)
- Supervisor logic tested by running script manually

### Automated Tests (Post-MVP)
- Unit tests for CRUD operations
- Integration tests for API endpoints
- End-to-end tests for supervisor loop
- Board state validation tests

---

## 🚀 Deployment Notes

### Local Development
```bash
# Backend
cd backend
source .venv/bin/activate  # or: python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Frontend (static file serving)
cd frontend
python -m http.server 8002

# Supervisor (separate terminal)
./scripts/supervisor.sh
```

### Production Deployment
- Same setup, no `--reload` flag
- Use gunicorn or uvicorn without reload:
  ```bash
  gunicorn "main:app" -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
  ```
- Supervisor cron as system service or crontab entry

---

## 📝 Design Decisions Rationale

### Why SQLite vs PostgreSQL?
**Decision**: Use SQLite for MVP  
**Why**: 
- Zero-config deployment (single file)
- Sufficient for single-user local operation
- Easy to backup/restore (copy .db file)
- SQLModel provides full ORM support
- Can migrate to Postgres later if needed

### Why FastAPI over Flask?
**Decision**: Use FastAPI  
**Why**:
- Automatic API documentation (Swagger/OpenAPI)
- Type hints with Pydantic validation
- Async/await support for scalability
- Modern Python ecosystem

### Why Vanilla JS vs Framework?
**Decision**: Use vanilla HTML/CSS/JS for MVP  
**Why**:
- No build step required
- Single files are inspectable and editable
- Full functionality without framework overhead
- Can add React/Vue later if needed

### Why WIP Limit = 1 for MVP?
**Decision**: One card per agent at a time  
**Why**:
- Prevents context switching
- Focus on one unit of work
- Simplifies supervisor logic initially
- Can increase later based on empirical data

---

*Last updated: Quinn 3.5 — 2026-03-14 10:30 CST*  
*Milestone: Architecture documented and ready for MVP implementation*  
*Next milestone: Build MVP frontend UI*
