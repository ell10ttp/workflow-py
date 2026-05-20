"""Regression tests for the DLQ failure callback empty-body crash.

When QStash delivers a failure callback whose ``body`` field is truthy but
base64-decodes to an empty string, ``_handle_failure`` used to call
``json.loads("")`` and raise ``json.decoder.JSONDecodeError``. The exception
was swallowed into a 500 by ``_safe_handler``, so the registered
``failure_function`` never ran. These tests pin the fix: an empty decoded body
degrades to ``{}`` and the failure function still runs.
"""

import base64
import json

import pytest

from upstash_workflow.constants import WORKFLOW_FAILURE_HEADER
from upstash_workflow.error import WorkflowAbort
from upstash_workflow.workflow_types import _AsyncRequest, _SyncRequest

# The exact incident shape: a *truthy* body that base64-decodes to "".
# base64 ignores its non-alphabet whitespace, so "\n" decodes to b"".
# This slips past the `if body else "{}"` guard (body is truthy) and
# produces json.loads("") -> JSONDecodeError "char 0".
_EMPTY_DECODING_BODY = "\n"

# A truthy body that base64-decodes to a blank (whitespace) string.
_WHITESPACE_BODY = base64.b64encode(b"   ").decode()


def _callback_payload(body: str) -> str:
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


async def _route_function(context):
    # Mimic a real workflow: first step aborts immediately so
    # try_authentication returns "step-found".
    raise WorkflowAbort("disabled-qstash-worklfow-run")


class TestAsyncHandleFailureEmptyBody:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("body", [_EMPTY_DECODING_BODY, _WHITESPACE_BODY, None])
    async def test_empty_body_does_not_crash_and_runs_failure_function(
        self, body
    ) -> None:
        from upstash_workflow.asyncio.workflow_parser import _handle_failure

        called = {}

        async def failure_function(context, status, error_message, header):
            called["status"] = status
            called["error_message"] = error_message

        request_payload = _callback_payload(body)
        request = _AsyncRequest(
            _body=request_payload.encode(),
            headers={WORKFLOW_FAILURE_HEADER: "true"},
        )

        result = await _handle_failure(
            request,
            request_payload,
            qstash_client=None,
            initial_payload_parser=lambda p: p,
            route_function=_route_function,
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
    def test_empty_body_does_not_crash_and_runs_failure_function(self, body) -> None:
        from upstash_workflow.workflow_parser import _handle_failure

        called = {}

        def failure_function(context, status, error_message, header):
            called["status"] = status
            called["error_message"] = error_message

        def route_function(context):
            raise WorkflowAbort("disabled-qstash-worklfow-run")

        request_payload = _callback_payload(body)
        request = _SyncRequest(
            body=request_payload,
            headers={WORKFLOW_FAILURE_HEADER: "true"},
        )

        result = _handle_failure(
            request,
            request_payload,
            qstash_client=None,
            initial_payload_parser=lambda p: p,
            route_function=route_function,
            failure_function=failure_function,
            env={},
            retries=3,
        )

        assert result == "is-failure-callback"
        assert called["status"] == 500
        assert called["error_message"] is None
