# Plan: Add `invoke` Feature to Workflow Python SDK

## Context

This repo is a fork of the Upstash Workflow Python SDK. The JS SDK (`upstash/workflow-js`) supports `context.invoke()` — a method that lets one workflow call another workflow and wait for its result. This feature does not exist in the Python SDK yet.

**Problem**: Currently, the only way to call another workflow is via `context.call()`, which treats it as a generic HTTP request. There's no first-class workflow-to-workflow invocation with typed responses and status tracking (`is_failed`, `is_canceled`).

**Goal**: Port the `invoke` feature from the JS SDK to match its semantics — new `"Invoke"` step type, `context.invoke()` method, `InvokableWorkflow` wrapper, and `serve_many` for multi-workflow routing.

---

## How Invoke Works (JS SDK Reference)

1. `createWorkflow(fn)` wraps a route function into an `InvokableWorkflow` with no `workflowId` yet
2. `serveMany({ "wf1": workflow1, "wf2": workflow2 })` assigns `workflowId`s and creates a single endpoint that routes by last URL path segment
3. `context.invoke("step", { workflow: wf2, body: {...} })` creates a `LazyInvokeStep` that:
   - Derives the child URL by replacing the last path segment of the parent URL with the child's `workflowId`
   - Publishes a message to QStash targeting the child URL with headers: `Upstash-Workflow-Invoke: true`, `Upstash-Workflow-Invoke-Count: N+1`
   - Sets callback headers so the child's result is delivered back to the parent
4. The child runs as a normal workflow. On completion, QStash delivers the result back via callback
5. Parent resumes with `InvokeStepResponse { body, is_failed, is_canceled }`

---

## Implementation Phases

### Phase 1: Core Types and Constants

**Files:**
- `upstash_workflow/constants.py` — Add header constants:
  ```python
  WORKFLOW_INVOKE_HEADER = "Upstash-Workflow-Invoke"
  WORKFLOW_INVOKE_COUNT_HEADER = "Upstash-Workflow-Invoke-Count"
  ```

- `upstash_workflow/types.py`:
  - Add `"Invoke"` to `StepTypes` list and `StepType` Literal
  - Add invoke fields to `Step` dataclass: `invoke_url`, `invoke_body`, `invoke_headers`
  - Add `InvokeStepResponse` dataclass: `body`, `is_failed: bool = False`, `is_canceled: bool = False`
  - Add `InvokableWorkflow` dataclass: `route_function`, `workflow_id: Optional[str] = None`

### Phase 2: Lazy Step Classes (sync + async)

**Files:**
- `upstash_workflow/context/steps.py` — Add `_LazyInvokeStep`:
  - `step_type = "Invoke"`
  - Constructor: `step_name`, `url` (target workflow URL), `body`, `headers`, `retries`
  - `get_result_step` populates `invoke_url`, `invoke_body`, `invoke_headers` on Step
- `upstash_workflow/asyncio/context/steps.py` — Async mirror (trivially async since no user function executed)

### Phase 3: Context Method + Auto Executor

**Files:**
- `upstash_workflow/context/context.py` — Add `context.invoke()`:
  ```python
  def invoke(self, step_name, *, workflow, body=None, headers=None, retries=None) -> InvokeStepResponse
  ```
  - Validates `workflow.workflow_id` is set (raises `WorkflowError` if not)
  - Derives child URL: replace last path segment of `self.url` with `workflow.workflow_id`
  - Creates `_LazyInvokeStep`, passes to `_add_step`
  - Parses result into `InvokeStepResponse`

- `upstash_workflow/asyncio/context/context.py` — Async mirror

- `upstash_workflow/context/auto_executor.py`:
  - Import `_LazyInvokeStep`
  - In `submit_steps_to_qstash`: add branch for invoke steps (`single_step.invoke_url`) — use `publish_json()` directly instead of `batch_json()` to match JS SDK behavior
  - Handle `_LazyInvokeStep` in retries/timeout isinstance checks

- `upstash_workflow/asyncio/context/auto_executor.py` — Async mirror

### Phase 4: Header Construction + Callback Handling

**Files:**
- `upstash_workflow/workflow_requests.py`:
  - `_get_headers()`: Add branch for `step.invoke_url` (similar to existing `step.call_url` branch):
    - Set `Upstash-Workflow-Invoke: true` forwarded to child
    - Set `Upstash-Workflow-Init: true` (child is a new workflow run)
    - Set callback headers pointing back to parent workflow URL
    - Forward user-specified invoke headers with `Upstash-Forward-` prefix
  - `_handle_third_party_call_result()`: Add check for `step_type == "Invoke"` — format result as `{ body, is_failed, is_canceled }` instead of `{ status, body, header }`

- `upstash_workflow/asyncio/workflow_requests.py` — Mirror callback handling changes

### Phase 5: `serve_many` + Framework Integration

**Files:**
- `upstash_workflow/serve/serve.py` — Add `serve_many()`:
  ```python
  def serve_many(workflows: Dict[str, InvokableWorkflow], **options) -> Dict[str, Callable]
  ```
  - Assigns `workflow_id` to each workflow
  - Creates a handler per workflow via `_serve_base`
  - Returns a router that extracts last URL path segment and dispatches

- `upstash_workflow/asyncio/serve/serve.py` — Add `async_serve_many()`

- `upstash_workflow/fastapi.py` — Add `Serve.serve_many(path, workflows, **opts)`:
  - Registers a single FastAPI route at `path/{workflow_id}`
  - Routes to correct workflow handler

- `upstash_workflow/flask.py` — Add `Serve.serve_many(path, workflows, **opts)`:
  - Registers Flask route with `<workflow_id>` path variable

- Add `create_workflow()` and `create_async_workflow()` helper functions (can live in types.py or a new module)

### Phase 6: Exports

**File:** `upstash_workflow/__init__.py`
- Export: `InvokeStepResponse`, `InvokableWorkflow`, `create_workflow`, `create_async_workflow`, `serve_many`, `async_serve_many`

### Phase 7: Tests + Examples

- Unit tests for `_LazyInvokeStep` (sync + async)
- Unit tests for `InvokeStepResponse`, `InvokableWorkflow`
- Integration tests for `context.invoke()` with mocked QStash
- Integration tests for `serve_many` routing
- Update `examples/fastapi/main.py` and `examples/flask/main.py`

---

## File Change Summary

| File | Change |
|------|--------|
| `constants.py` | +2 header constants |
| `types.py` | Add `"Invoke"` to StepType, add invoke fields to Step, add `InvokeStepResponse`, `InvokableWorkflow` |
| `context/steps.py` | Add `_LazyInvokeStep` |
| `asyncio/context/steps.py` | Add async `_LazyInvokeStep` |
| `context/context.py` | Add `invoke()` method + URL derivation |
| `asyncio/context/context.py` | Add async `invoke()` method |
| `context/auto_executor.py` | Handle invoke steps (use `publish_json` instead of batch) |
| `asyncio/context/auto_executor.py` | Mirror |
| `workflow_requests.py` | Add invoke branch in `_get_headers`, invoke result handling in `_handle_third_party_call_result` |
| `asyncio/workflow_requests.py` | Mirror callback handling |
| `serve/serve.py` | Add `serve_many()` |
| `asyncio/serve/serve.py` | Add `async_serve_many()` |
| `fastapi.py` | Add `Serve.serve_many()` |
| `flask.py` | Add `Serve.serve_many()` |
| `__init__.py` | New exports |

---

## Key Design Decisions

1. **`publish_json` over `batch_json` for invoke**: JS SDK uses `publish()` for invoke steps. We should match this to avoid any QStash behavioral differences.

2. **`serve_many` required for invoke**: Workflows must be registered via `serve_many` to get a `workflow_id`. Invoking an unregistered workflow raises `WorkflowError`.

3. **URL derivation**: Replace last path segment of parent URL with child's `workflow_id`. Same logic as JS SDK.

4. **`"Invoke"` as first-class step type**: Not a variant of `"Call"` — gets its own StepType, LazyStep class, and response type.

---

## Risks / Open Questions

1. **QStash callback format for invoke results**: Need to verify the exact shape of the callback message when a child workflow completes. The JS SDK may rely on specific QStash behavior for invoke callbacks that differs from call callbacks. Should test against actual QStash.

2. **Invoke count threading**: The `Invoke-Count` header needs to be read from the incoming request before `_recreate_user_headers` strips it. May need to extract it in `_validate_request` or pass raw headers separately.

3. **Child workflow completion signaling**: In the JS SDK, the child workflow's final result is delivered via QStash callback. Need to confirm the Python SDK's `_trigger_workflow_delete` + callback mechanism produces the same behavior.

4. **Sync/async duplication burden**: 11 files need changes, most mirrored. This is inherent to the SDK's architecture.

---

## Verification

1. Write a FastAPI example with two workflows where workflow A invokes workflow B
2. Run with a real QStash token against a local tunnel (ngrok/cloudflared)
3. Verify: parent pauses at invoke step, child executes, result flows back, parent resumes with `InvokeStepResponse`
4. Test error case: child workflow fails, parent gets `is_failed=True`
5. Run existing tests to confirm no regressions
