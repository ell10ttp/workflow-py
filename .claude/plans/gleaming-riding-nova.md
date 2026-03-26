# Add `get_waiters()` to Python Workflow SDK

## Context

This Python SDK is a fork of the Upstash Workflow Python SDK. It already has `wait_for_event()`, `notify()`, and `Client.notify()` implemented. The JS SDK (`workflow-js`) additionally supports a `client.getWaiters()` method documented at [upstash.com/docs/workflow/basics/client/waiters](https://upstash.com/docs/workflow/basics/client/waiters) that queries which workflows are currently waiting for a given event. The JS SDK also supports a `workflowRunId` lookback parameter on `notify()` and has a richer `Waiter` type.

## Continuity Ledger

`thoughts/ledgers/CONTINUITY_CLAUDE-get-waiters.md`

## Gap Analysis: Python SDK vs JS SDK

| Feature | JS SDK | Python SDK | Status |
|---------|--------|------------|--------|
| `context.wait_for_event()` | Yes | Yes | Done |
| `context.notify()` | Yes | Yes | Done |
| `Client.notify()` | Yes | Yes | Done |
| **`Client.get_waiters(event_id)`** | Yes | **No** | **Missing** |
| **`Waiter` type** | Full type with url, deadline, headers, timeoutUrl, etc. | Only partial fields on `NotifyResponse` | **Incomplete** |
| **`workflowRunId` on notify (lookback)** | Yes, on both `Client.notify()` and `context.notify()` | **No** | **Missing** |
| **`error` field on `NotifyResponse`** | Yes | **No** | **Missing** |

---

## Execution Workflow

**Skill:** `superpowers:executing-plans` — batch execution with review checkpoints.
**Editing:** Use `morph-apply` for file edits where the file is already understood and >200 lines, otherwise use Edit tool for small precise edits on files already in context.
**Testing:** Delegate test runs to a **sub-agent** (`general-purpose`) to keep main context clean.
**Final step:** `/verification-before-completion` before marking work done.

---

## Batch 1: Types + Client (core data layer)

### Task 1.1: Add `Waiter` dataclass to `types.py`

**File:** `upstash_workflow/types.py`

Add before `NotifyResponse`:
```python
@dataclass
class Waiter:
    url: str
    deadline: int
    headers: Dict[str, List[str]]
    timeout_url: Optional[str] = None
    timeout_body: Optional[Any] = None
    timeout_headers: Optional[Dict[str, List[str]]] = None
```

Add `List` to typing imports if not present.

### Task 1.2: Update `NotifyResponse` in `types.py`

**File:** `upstash_workflow/types.py`

Replace existing `NotifyResponse`:
```python
@dataclass
class NotifyResponse:
    waiter: Waiter
    message_id: str
    error: str
```

**Breaking change**: flat `waiter_url`/`waiter_deadline` -> nested `Waiter` object. Matches actual QStash API response shape.

### Task 1.3: Add `get_waiters()` + update `notify()` on `Client` and `AsyncClient`

**File:** `upstash_workflow/client.py`

Changes:
1. Import `Waiter` from types
2. Add `workflow_run_id: Optional[str] = None` param to both `Client.notify()` and `AsyncClient.notify()`
3. Update URL construction: `POST /v2/notify/{workflowRunId}/{eventId}` when `workflow_run_id` provided, else `POST /v2/notify/{eventId}`
4. Update `NotifyResponse` parsing to create nested `Waiter` object from response JSON
5. Add `get_waiters(event_id)` to `Client` — `GET /v2/waiters/{eventId}`, returns `List[Waiter]`
6. Add `async get_waiters(event_id)` to `AsyncClient` — same endpoint, async

Helper for parsing waiter JSON into `Waiter` dataclass:
```python
def _parse_waiter(data: dict) -> Waiter:
    return Waiter(
        url=data.get("url", ""),
        deadline=data.get("deadline", 0),
        headers=data.get("headers", {}),
        timeout_url=data.get("timeoutUrl"),
        timeout_body=data.get("timeoutBody"),
        timeout_headers=data.get("timeoutHeaders"),
    )
```

### Task 1.4: Update `__init__.py` exports

**File:** `upstash_workflow/__init__.py`

Add `Waiter` to imports and `__all__`.

### Batch 1 Verification

**Sub-agent:** Run `uv run pytest tests/ -v` to check no import errors and existing tests still pass (they may fail if tests reference old `NotifyResponse` fields — that's expected and will be fixed in Batch 3).

---

## Batch 2: Context + Steps (workflow-level integration)

### Task 2.1: Update `_LazyNotifyStep` — sync

**File:** `upstash_workflow/context/steps.py`

Add `workflow_run_id: Optional[str] = None` to `_LazyNotifyStep.__init__()`. Store as `self.workflow_run_id`.

### Task 2.2: Update `_LazyNotifyStep` — async

**File:** `upstash_workflow/asyncio/context/steps.py`

Mirror the same change.

### Task 2.3: Update `context.notify()` — sync

**File:** `upstash_workflow/context/context.py`

Add `workflow_run_id: Optional[str] = None` param to `notify()`. Pass through to `_LazyNotifyStep`.

### Task 2.4: Update `context.notify()` — async

**File:** `upstash_workflow/asyncio/context/context.py`

Mirror the same change.

### Batch 2 Verification

**Sub-agent:** Run `uv run pytest tests/ -v` — expect some test failures from `NotifyResponse` shape change. Note failures for Batch 3.

---

## Batch 3: Tests + Final verification

### Task 3.1: Update existing tests for `NotifyResponse` shape change

**File:** `tests/test_wait_for_event.py`

Find all references to old `NotifyResponse` fields (`waiter_url`, `waiter_deadline`) and update to use nested `Waiter` object.

### Task 3.2: Add tests for `get_waiters()`

**File:** `tests/test_wait_for_event.py`

Add tests:
- `test_client_get_waiters` — mock `GET /v2/waiters/{eventId}`, verify returns `List[Waiter]`
- `test_async_client_get_waiters` — async variant
- `test_waiter_dataclass` — verify `Waiter` fields

### Task 3.3: Add tests for `workflow_run_id` lookback

**File:** `tests/test_wait_for_event.py`

Add tests:
- `test_client_notify_with_workflow_run_id` — verify URL is `/v2/notify/{workflowRunId}/{eventId}`
- `test_client_notify_without_workflow_run_id` — verify URL remains `/v2/notify/{eventId}`
- `test_context_notify_with_workflow_run_id` — verify param passes through to step

### Task 3.4: Run full test suite

**Sub-agent:** Run `uv run pytest tests/ -v` — all tests must pass.

---

## Batch 4: Final Verification

### Task 4.1: `/verification-before-completion`

Invoke `superpowers:verification-before-completion` skill. This includes:
- Run full test suite and confirm green
- Review all changed files against the plan
- Confirm no regressions in existing functionality
- Evidence before assertions

### Task 4.2: Update continuity ledger

Mark all phases complete in `thoughts/ledgers/CONTINUITY_CLAUDE-get-waiters.md`.

### Task 4.3: `/commit` when verified

Use the `/commit` skill per git-commits rule.

---

## Files to Modify

| File | Change |
|------|--------|
| `upstash_workflow/types.py` | Add `Waiter` dataclass, update `NotifyResponse` |
| `upstash_workflow/client.py` | Add `get_waiters()`, add `workflow_run_id` to `notify()`, update response parsing |
| `upstash_workflow/context/context.py` | Add `workflow_run_id` param to `notify()` |
| `upstash_workflow/context/steps.py` | Add `workflow_run_id` to `_LazyNotifyStep` |
| `upstash_workflow/asyncio/context/context.py` | Add `workflow_run_id` param to `notify()` |
| `upstash_workflow/asyncio/context/steps.py` | Add `workflow_run_id` to `_LazyNotifyStep` |
| `upstash_workflow/__init__.py` | Export `Waiter` |
| `tests/test_wait_for_event.py` | Update `NotifyResponse` tests, add `get_waiters()` + lookback tests |
