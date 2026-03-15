# agent-board

`agent-board` is a standalone project inside DIMINOCLAW for managing agent work through a real board application instead of scattered notes or ad hoc tickets.

The goal is to build a local-first system with:
- a human-visible board UI
- structured work cards
- clear ownership and status tracking
- execution logs and next-step tracking
- supervisor logic for choosing the next actionable work
- cron-compatible continuation so the project can keep moving incrementally

## Purpose

This project exists to become the operational control center for agent work.

Instead of relying on fragile conversational continuity, the system should make work visible and durable through code, files, and persistent state.

The board should eventually support:
- BACKLOG
- READY
- IN_PROGRESS
- BLOCKED
- REVIEW
- DONE

Each card should eventually support:
- title
- type
- priority
- owner
- role
- status
- dependencies
- acceptance criteria
- execution log
- blockers
- next step
- timestamps

## Current Project Principles

- Files are the source of truth.
- The system should be inspectable by a human at any time.
- The project should progress through small real increments.
- No invisible work.
- No vague “planning only” runs.
- Each run should leave the project in a resumable state.

## Core Project Files

These files are important for continuity:

- `CURRENT_STATE.md` — the exact next step and current handoff state
- `LIVING_PROGRESS_LOG.md` — chronological record of real work completed
- `ARCHITECTURE.md` — current technical design decisions
- `ROADMAP.md` — milestone status and upcoming priorities
- `README.md` — project overview and operating instructions

## Expected Structure

Current and planned structure:

```text
agent-board/
  frontend/
  backend/
  scripts/
  docs/
  logs/
  data/
  memory/
  session_logs/

  README.md
  CURRENT_STATE.md
  ARCHITECTURE.md
  ROADMAP.md
  LIVING_PROGRESS_LOG.md
