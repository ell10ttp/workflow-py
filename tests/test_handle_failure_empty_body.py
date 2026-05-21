"""Regression tests for the DLQ failure callback empty-body crash.

When QStash delivers a failure callback whose ``body`` field is truthy but
base64-decodes to an empty string, ``_handle_failure`` used to call
``json.loads("")`` and raise ``json.decoder.JSONDecodeError``. The exception
was swallowed into a 500 by ``_safe_handler``, so the registered
``failure_function`` never ran. These tests pin the fix: an empty decoded body
degrades to ``{}`` and the failure function still runs.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional

import pytest
from qstash import AsyncQStash, QStash

from upstash_workflow import AsyncWorkflowContext, WorkflowContext
from upstash_workflow.constants import WORKFLOW_FAILURE_HEADER
from upstash_workflow.error import WorkflowAbort
from upstash_workflow.workflow_types import _AsyncRequest, _SyncRequest

from tests.utils import MOCK_QSTASH_SERVER_URL

# The exact incident shape: a *truthy* body that base64-decodes to "".
# base64 ignores its non-alphabet whitespace, so "\n" decodes to b"".
# This slips past the `if body else "{}"` guard (body is truthy) and
# produces json.loads("") -> JSONDecodeError "char 0".
_EMPTY_DECODING_BODY = "\n"

# A truthy body that base64-decodes to a blank (whitespace) string.
_WHITESPACE_BODY = base64.b64encode(b"   ").decode()

# This must match _DisabledWorkflowContext.__disabled_message in the SDK
# (upstash_workflow/.../serve/authorization.py) verbatim. The SDK's own
# constant contains the misspelling "worklfow"; raising WorkflowAbort with
# any other string makes try_authentication treat it as a real step failure.
# Do NOT "correct" the spelling here — it would break the test.
_SDK_DISABLED_ABORT_MESSAGE = "disabled-qstash-worklfow-run"


def _callback_payload(body: Optional[str]) -> str:
    return json.dumps(
        {
            "status": 500,
            "header": {},
            "body": body,
            "url": "https://example.com/agent-signer-setup",
            "sourceBody": "",
            "workflowRunId": "wfr_test",
        }
    )


class TestAsyncHandleFailureEmptyBody:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("body", [_EMPTY_DECODING_BODY, _WHITESPACE_BODY, None])
    async def test_empty_body_does_not_crash_and_runs_failure_function(
        self, body: Optional[str]
    ) -> None:
        from upstash_workflow.asyncio.workflow_parser import _handle_failure

        called: Dict[str, Any] = {}

        async def failure_function(
            context: AsyncWorkflowContext[Any],
            status: int,
            error_message: Optional[str],
            header: Dict[str, str],
        ) -> None:
            called["status"] = status
            called["error_message"] = error_message

        async def route_function(context: AsyncWorkflowContext[Any]) -> None:
            # Mimic a real workflow: first step aborts immediately so
            # try_authentication returns "step-found".
            raise WorkflowAbort(_SDK_DISABLED_ABORT_MESSAGE)

        request_payload = _callback_payload(body)
        request = _AsyncRequest(
            _body=request_payload.encode(),
            headers={WORKFLOW_FAILURE_HEADER: "true"},
        )

        result = await _handle_failure(
            request,
            request_payload,
            qstash_client=AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL),
            initial_payload_parser=lambda p: p,
            route_function=route_function,
            failure_function=failure_function,
            env={},
            retries=3,
        )

        assert result == "is-failure-callback"
        assert called["status"] == 500
        # Empty error payload -> message is absent, not a crash.
        assert called["error_message"] is None


class TestSyncHandleFailureEmptyBody:
    @pytest.mark.parametrize("body", [_EMPTY_DECODING_BODY, _WHITESPACE_BODY, None])
    def test_empty_body_does_not_crash_and_runs_failure_function(
        self, body: Optional[str]
    ) -> None:
        from upstash_workflow.workflow_parser import _handle_failure

        called: Dict[str, Any] = {}

        def failure_function(
            context: WorkflowContext[Any],
            status: int,
            error_message: Optional[str],
            header: Dict[str, str],
        ) -> None:
            called["status"] = status
            called["error_message"] = error_message

        def route_function(context: WorkflowContext[Any]) -> None:
            raise WorkflowAbort(_SDK_DISABLED_ABORT_MESSAGE)

        request_payload = _callback_payload(body)
        request = _SyncRequest(
            body=request_payload,
            headers={WORKFLOW_FAILURE_HEADER: "true"},
        )

        result = _handle_failure(
            request,
            request_payload,
            qstash_client=QStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL),
            initial_payload_parser=lambda p: p,
            route_function=route_function,
            failure_function=failure_function,
            env={},
            retries=3,
        )

        assert result == "is-failure-callback"
        assert called["status"] == 500
        assert called["error_message"] is None
