
---

## ROADMAP.md

```md
# agent-board roadmap

## Project Status

Current phase: Foundation / MVP bootstrapping

Primary objective:
Build a working standalone board application inside DIMINOCLAW that can become the execution system for agent work.

---

## NOW

### 1. Establish project foundation ✅ **COMPLETE**
- [x] Create clean project structure
- [x] Create required continuity files
- [x] Make project state easy to resume from files
- [x] Add scripts and entrypoints for repeatable work

### 2. Build backend MVP ✅ **COMPLETE**
- [x] Create backend app entrypoint
- [x] Add health endpoint
- [x] Add initial card model
- [x] Add basic CRUD path for cards
- [x] Verify backend can start cleanly

### 3. Build frontend MVP
- [ ] Create minimal frontend app shell
- [ ] Create board page
- [ ] Show board columns
- [ ] Display placeholder or live card data
- [ ] Verify frontend loads cleanly

### 4. Connect frontend and backend
- [ ] Fetch cards from backend
- [ ] Render cards by status
- [ ] Verify end-to-end vertical slice works

---

## NEXT

### 5. Add persistence
- [ ] Choose and document MVP persistence layer
- [ ] Create initial storage schema
- [ ] Persist cards across runs
- [ ] Add seed or default board data if needed

### 6. Add card detail capabilities
- [ ] Support richer card fields
- [ ] Add acceptance criteria structure
- [ ] Add execution log storage
- [ ] Add blockers and next-step fields

### 7. Add supervisor layer
- [ ] Create supervisor entrypoint
- [ ] Read board state
- [ ] Select next actionable work
- [ ] Respect WIP limits
- [ ] Log decisions and actions

---

## LATER

### 8. Add subagent orchestration support
- [ ] Track owners and roles more explicitly
- [ ] Represent active runs
- [ ] Add one-card-per-subagent assignment logic
- [ ] Add blocked/review/done transition enforcement

### 9. Improve usability
- [ ] Better board styling
- [ ] Card editing UX
- [ ] Filters and sorting
- [ ] Activity history view
- [ ] Current run / current focus panel

### 10. Improve operational reliability
- [ ] Add cron-safe wrapper scripts
- [ ] Add better startup checks
- [ ] Add logging and run summaries
- [ ] Add recovery behavior for partial failures

---

## BLOCKED / RISKS

### Current risks
- Automated runs may spend too much time re-orienting if continuity files are weak
- Sparse structure may cause repeated inspection instead of implementation
- Cron session continuity may not be fully reliable on its own

### Mitigation
- Keep `CURRENT_STATE.md` small and precise
- Keep `LIVING_PROGRESS_LOG.md` accurate
- Define exact next step after each run
- Prefer one concrete deliverable per run

---

## Definition of MVP

MVP is complete when:
- frontend exists and loads
- backend exists and runs
- board columns render
- cards can be read from persistent or semi-persistent state
- one end-to-end vertical slice works
- supervisor entrypoint exists
- continuity files accurately describe the current system

---

## Working Rule

If work is completed, update this roadmap so it reflects reality.
If priorities change, update the order here instead of relying on memory.
