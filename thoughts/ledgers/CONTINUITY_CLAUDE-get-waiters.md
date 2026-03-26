# Session: get-waiters
Updated: 2026-03-26T17:10:33.909Z

## Goal
Add `Client.get_waiters()` / `AsyncClient.get_waiters()`, the `Waiter` type, and `workflowRunId` lookback support to the Python Workflow SDK — matching the JS SDK's waiters feature.

## Constraints
- Mirror all changes in both sync and async variants
- Match the QStash API contract: `GET /v2/waiters/{eventId}`, `POST /v2/notify/{workflowRunId}/{eventId}`
- Follow existing code patterns (httpx for Client, dataclasses for types)

## Key Decisions
- Breaking `NotifyResponse` change accepted: flat fields -> nested `Waiter` object to match actual QStash API shape
- Added `_parse_waiter` and `_parse_notify_response` helpers in `client.py` for DRY parsing

## State
- Done:
  - [x] Batch 1: Types + Client (Waiter dataclass, NotifyResponse update, get_waiters, workflow_run_id on notify, exports)
  - [x] Batch 2: Context + Steps (workflow_run_id on _LazyNotifyStep and context.notify, sync + async)
  - [x] Batch 3: Tests (24 new tests, all passing)
  - [x] Batch 4: Verification (65/67 pass, 2 pre-existing failures)
- Now: [→] Commit
- Next: Done

## Open Questions
- None remaining

## Working Set
- Branch: `master`
- Key files: `upstash_workflow/types.py`, `upstash_workflow/client.py`, `upstash_workflow/context/context.py`, `upstash_workflow/asyncio/context/context.py`
- Test cmd: `uv run pytest tests/ -v`
- Current Plan File: `~/.claude/plans/gleaming-riding-nova.md`
