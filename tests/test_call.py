import inspect
import json
from dataclasses import is_dataclass
from typing import get_type_hints

import pytest
from qstash import QStash

from upstash_workflow import WorkflowContext, AsyncWorkflowContext, CallResponse
from upstash_workflow.error import WorkflowAbort
from upstash_workflow.types import CallResponseDict, FlowControl
from upstash_workflow.context.steps import _LazyCallStep as SyncLazyCallStep
from upstash_workflow.asyncio.context.steps import _LazyCallStep as AsyncLazyCallStep
from tests.utils import (
    mock_qstash_server,
    RequestFields,
    ResponseFields,
    MOCK_QSTASH_SERVER_URL,
    MOCK_QSTASH_SERVER_PORT,
    WORKFLOW_ENDPOINT,
)


class TestCallResponseType:
    def test_call_response_is_dataclass(self) -> None:
        assert is_dataclass(CallResponse)

    def test_call_response_construction_and_field_access(self) -> None:
        response = CallResponse(
            status=200,
            body={"key": "value"},
            header={"content-type": ["application/json"]},
        )
        assert response.status == 200
        assert response.body == {"key": "value"}
        assert response.header == {"content-type": ["application/json"]}

    def test_call_response_with_string_body(self) -> None:
        response = CallResponse(status=404, body="not found", header={})
        assert response.status == 404
        assert response.body == "not found"
        assert response.header == {}

    def test_call_response_with_list_body(self) -> None:
        response = CallResponse(status=200, body=[1, 2, 3], header={"x-custom": ["a", "b"]})
        assert response.body == [1, 2, 3]

    def test_call_response_with_none_body(self) -> None:
        response = CallResponse(status=204, body=None, header={})
        assert response.body is None

    def test_call_response_header_contains_lists(self) -> None:
        headers = {
            "content-type": ["application/json"],
            "set-cookie": ["a=1", "b=2"],
        }
        response = CallResponse(status=200, body="ok", header=headers)
        assert len(response.header["set-cookie"]) == 2


class TestCallResponseDictType:
    def test_call_response_dict_has_correct_keys(self) -> None:
        hints = get_type_hints(CallResponseDict)
        assert "status" in hints
        assert "body" in hints
        assert "header" in hints

    def test_call_response_dict_can_be_constructed(self) -> None:
        d: CallResponseDict = {
            "status": 200,
            "body": "hello",
            "header": {"x-foo": ["bar"]},
        }
        assert d["status"] == 200
        assert d["body"] == "hello"
        assert d["header"] == {"x-foo": ["bar"]}


class TestSyncLazyCallStep:
    def test_can_be_imported(self) -> None:
        assert SyncLazyCallStep is not None

    def test_has_call_step_type(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 0, None
        )
        assert step.step_type == "Call"

    def test_stores_url(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://api.example.com/data", "GET", None, {}, 0, None
        )
        assert step.url == "https://api.example.com/data"

    def test_stores_method(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "POST", None, {}, 0, None
        )
        assert step.method == "POST"

    def test_stores_body(self) -> None:
        body = {"key": "value"}
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "POST", body, {}, 0, None
        )
        assert step.body == {"key": "value"}

    def test_stores_headers(self) -> None:
        headers = {"Authorization": "Bearer token123"}
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, headers, 0, None
        )
        assert step.headers == {"Authorization": "Bearer token123"}

    def test_stores_retries(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 5, None
        )
        assert step.retries == 5

    def test_stores_timeout(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 0, "30s"
        )
        assert step.timeout == "30s"

    def test_stores_int_timeout(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 0, 60
        )
        assert step.timeout == 60

    def test_stores_none_timeout(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 0, None
        )
        assert step.timeout is None

    def test_get_plan_step_returns_step_with_call_type(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 0, None
        )
        plan_step = step.get_plan_step(concurrent=1, target_step=0)
        assert plan_step.step_type == "Call"
        assert plan_step.step_name == "call-step"
        assert plan_step.step_id == 0

    def test_get_plan_step_has_correct_concurrent_and_target(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 0, None
        )
        plan_step = step.get_plan_step(concurrent=3, target_step=7)
        assert plan_step.concurrent == 3
        assert plan_step.target_step == 7

    def test_get_result_step_has_call_fields(self) -> None:
        step = SyncLazyCallStep(
            "call-step",
            "https://api.example.com",
            "PATCH",
            {"data": "payload"},
            {"X-Custom": "header-val"},
            3,
            "10s",
        )
        result_step = step.get_result_step(concurrent=1, step_id=5)
        assert result_step.call_url == "https://api.example.com"
        assert result_step.call_method == "PATCH"
        assert result_step.call_body == {"data": "payload"}
        assert result_step.call_headers == {"X-Custom": "header-val"}
        assert result_step.step_id == 5
        assert result_step.step_type == "Call"


class TestAsyncLazyCallStep:
    def test_can_be_imported(self) -> None:
        assert AsyncLazyCallStep is not None

    def test_has_call_step_type(self) -> None:
        step = AsyncLazyCallStep(
            "async-call", "https://example.com", "GET", None, {}, 0, None
        )
        assert step.step_type == "Call"

    def test_stores_all_parameters(self) -> None:
        step = AsyncLazyCallStep(
            "async-call",
            "https://api.example.com/v2",
            "PUT",
            {"update": True},
            {"Auth": "token"},
            2,
            "15s",
        )
        assert step.url == "https://api.example.com/v2"
        assert step.method == "PUT"
        assert step.body == {"update": True}
        assert step.headers == {"Auth": "token"}
        assert step.retries == 2
        assert step.timeout == "15s"

    def test_get_plan_step_returns_call_type(self) -> None:
        step = AsyncLazyCallStep(
            "async-call", "https://example.com", "DELETE", None, {}, 0, None
        )
        plan_step = step.get_plan_step(concurrent=1, target_step=0)
        assert plan_step.step_type == "Call"

    @pytest.mark.asyncio
    async def test_get_result_step_has_call_fields(self) -> None:
        step = AsyncLazyCallStep(
            "async-call",
            "https://api.example.com",
            "POST",
            "body-data",
            {"Content-Type": "text/plain"},
            1,
            30,
        )
        result_step = await step.get_result_step(concurrent=1, step_id=3)
        assert result_step.call_url == "https://api.example.com"
        assert result_step.call_method == "POST"
        assert result_step.call_body == "body-data"
        assert result_step.call_headers == {"Content-Type": "text/plain"}
        assert result_step.step_id == 3


class TestSyncContextCallAPI:
    def test_workflow_context_has_call_method(self) -> None:
        assert hasattr(WorkflowContext, "call")
        assert callable(getattr(WorkflowContext, "call"))

    def test_call_parameter_names(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "step_name" in params
        assert "url" in params
        assert "method" in params
        assert "body" in params
        assert "headers" in params
        assert "retries" in params
        assert "timeout" in params

    def test_call_method_default(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert sig.parameters["method"].default == "GET"

    def test_call_body_default(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert sig.parameters["body"].default is None

    def test_call_headers_default(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert sig.parameters["headers"].default is None

    def test_call_retries_default(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert sig.parameters["retries"].default == 0

    def test_call_timeout_default(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert sig.parameters["timeout"].default is None

    def test_url_is_keyword_only(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert sig.parameters["url"].kind == inspect.Parameter.KEYWORD_ONLY


class TestAsyncContextCallAPI:
    def test_async_workflow_context_has_call_method(self) -> None:
        assert hasattr(AsyncWorkflowContext, "call")
        assert callable(getattr(AsyncWorkflowContext, "call"))

    def test_call_parameter_names(self) -> None:
        sig = inspect.signature(AsyncWorkflowContext.call)
        params = list(sig.parameters.keys())
        assert "step_name" in params
        assert "url" in params
        assert "method" in params
        assert "body" in params
        assert "headers" in params
        assert "retries" in params
        assert "timeout" in params

    def test_call_method_default(self) -> None:
        sig = inspect.signature(AsyncWorkflowContext.call)
        assert sig.parameters["method"].default == "GET"

    def test_call_retries_default(self) -> None:
        sig = inspect.signature(AsyncWorkflowContext.call)
        assert sig.parameters["retries"].default == 0

    def test_call_is_coroutine_function(self) -> None:
        assert inspect.iscoroutinefunction(AsyncWorkflowContext.call)


class TestSyncContextCallIntegration:
    @pytest.fixture
    def qstash_client(self) -> QStash:
        return QStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)

    def test_get_call_minimal_params(self, qstash_client: QStash) -> None:
        import http.server
        import socketserver
        import threading

        context = WorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-call-get",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        class CaptureHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                request_body_captured.append(json.loads(body))
                response = json.dumps([{"messageId": "msg-get", "deduplicated": False}])
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(response.encode())

            def log_message(self, format: str, *args: object) -> None:
                pass

        class ThreadedServer(socketserver.TCPServer):
            allow_reuse_address = True

        server = ThreadedServer(("localhost", MOCK_QSTASH_SERVER_PORT), CaptureHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            with pytest.raises(WorkflowAbort) as excinfo:
                context.call("get-step", url="https://httpbin.org/get")
            assert "Aborting workflow after executing step 'get-step'." in str(excinfo.value)

            assert len(request_body_captured) == 1
            batch_item = request_body_captured[0][0]
            assert batch_item["destination"] == "https://httpbin.org/get"
            assert batch_item["headers"]["Upstash-Method"] == "GET"
        finally:
            server.shutdown()
            server.server_close()

    def test_post_call_with_all_params(self, qstash_client: QStash) -> None:
        import http.server
        import socketserver
        import threading

        context = WorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-call-post",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        class CaptureHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                request_body_captured.append(json.loads(body))
                response = json.dumps([{"messageId": "msg-post", "deduplicated": False}])
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(response.encode())

            def log_message(self, format: str, *args: object) -> None:
                pass

        class ThreadedServer(socketserver.TCPServer):
            allow_reuse_address = True

        server = ThreadedServer(("localhost", MOCK_QSTASH_SERVER_PORT), CaptureHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            with pytest.raises(WorkflowAbort) as excinfo:
                context.call(
                    "post-step",
                    url="https://httpbin.org/post",
                    method="POST",
                    body={"key": "value", "num": 42},
                    headers={"X-Custom-Header": "custom-value"},
                    retries=3,
                    timeout="30s",
                )
            assert "Aborting workflow after executing step 'post-step'." in str(excinfo.value)

            assert len(request_body_captured) == 1
            batch_item = request_body_captured[0][0]
            assert batch_item["destination"] == "https://httpbin.org/post"
            headers = batch_item["headers"]
            assert headers["Upstash-Method"] == "POST"
            assert headers["Upstash-Forward-X-Custom-Header"] == "custom-value"
            assert headers["Upstash-Forward-Upstash-Retries"] == "3"
        finally:
            server.shutdown()
            server.server_close()

    def test_call_sends_correct_destination(self, qstash_client: QStash) -> None:
        context = WorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-call-dest",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        target_url = "https://api.third-party.com/webhook"

        request_body_captured = []

        import http.server
        import socketserver
        import threading

        class CaptureHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                request_body_captured.append(json.loads(body))
                response = json.dumps([{"messageId": "msg-456", "deduplicated": False}])
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(response.encode())

            def log_message(self, format: str, *args: object) -> None:
                pass

        class ThreadedServer(socketserver.TCPServer):
            allow_reuse_address = True

        server = ThreadedServer(("localhost", MOCK_QSTASH_SERVER_PORT), CaptureHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            with pytest.raises(WorkflowAbort):
                context.call("dest-step", url=target_url, method="PUT", body={"action": "test"})

            assert len(request_body_captured) == 1
            batch_item = request_body_captured[0][0]
            assert batch_item["destination"] == target_url
        finally:
            server.shutdown()
            server.server_close()


class TestAsyncContextCallIntegration:
    @pytest.mark.asyncio
    async def test_get_call_minimal_params(self) -> None:
        from qstash import AsyncQStash
        from aiohttp import web

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-async-get",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        async def capture_request(request: web.Request) -> web.Response:
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return web.json_response(
                data=[{"messageId": "msg-async-get", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort) as excinfo:
                await context.call("async-get-step", url="https://httpbin.org/get")
            assert "Aborting workflow after executing step 'async-get-step'." in str(excinfo.value)

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        assert batch_item["destination"] == "https://httpbin.org/get"

    @pytest.mark.asyncio
    async def test_post_call_with_all_params(self) -> None:
        from qstash import AsyncQStash
        from aiohttp import web

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-async-post",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        async def capture_request(request: web.Request) -> web.Response:
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return web.json_response(
                data=[{"messageId": "msg-async-post", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort) as excinfo:
                await context.call(
                    "async-post-step",
                    url="https://api.example.com/data",
                    method="POST",
                    body={"key": "value", "nested": {"a": 1}},
                    headers={"X-Api-Key": "secret-key"},
                    retries=5,
                    timeout="60s",
                )
            assert "Aborting workflow after executing step 'async-post-step'." in str(excinfo.value)

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        assert batch_item["destination"] == "https://api.example.com/data"
        headers = batch_item["headers"]
        assert headers["Upstash-Method"] == "POST"
        assert "Upstash-Forward-X-Api-Key" in headers
        assert headers["Upstash-Forward-X-Api-Key"] == "secret-key"
        assert headers["Upstash-Forward-Upstash-Retries"] == "5"

    @pytest.mark.asyncio
    async def test_call_sends_method_header(self) -> None:
        from qstash import AsyncQStash
        from aiohttp import web

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-async-method",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        async def capture_request(request: web.Request) -> web.Response:
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return web.json_response(
                data=[{"messageId": "msg-method", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort):
                await context.call(
                    "delete-step",
                    url="https://api.example.com/resource/123",
                    method="DELETE",
                )

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        assert batch_item["headers"]["Upstash-Method"] == "DELETE"

    @pytest.mark.asyncio
    async def test_call_includes_callback_step_metadata(self) -> None:
        from qstash import AsyncQStash
        from aiohttp import web

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-async-meta",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        async def capture_request(request: web.Request) -> web.Response:
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return web.json_response(
                data=[{"messageId": "msg-meta", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort):
                await context.call(
                    "meta-step",
                    url="https://api.example.com/endpoint",
                    method="GET",
                )

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        headers = batch_item["headers"]
        assert headers["Upstash-Forward-Upstash-Callback-Forward-Upstash-Workflow-StepType"] == "Call"
        assert headers["Upstash-Forward-Upstash-Callback-Forward-Upstash-Workflow-StepName"] == "meta-step"
        assert headers["Upstash-Forward-Upstash-Workflow-CallType"] == "toCallback"


class TestFlowControlType:
    def test_flow_control_is_dataclass(self) -> None:
        assert is_dataclass(FlowControl)

    def test_flow_control_construction_with_all_fields(self) -> None:
        fc = FlowControl(key="openai-limiter", rate=50, parallelism=10, period="1m")
        assert fc.key == "openai-limiter"
        assert fc.rate == 50
        assert fc.parallelism == 10
        assert fc.period == "1m"

    def test_flow_control_defaults(self) -> None:
        fc = FlowControl(key="my-key")
        assert fc.rate is None
        assert fc.parallelism is None
        assert fc.period is None

    def test_flow_control_with_only_rate(self) -> None:
        fc = FlowControl(key="rate-only", rate=100)
        assert fc.rate == 100
        assert fc.parallelism is None

    def test_flow_control_with_only_parallelism(self) -> None:
        fc = FlowControl(key="parallel-only", parallelism=5)
        assert fc.parallelism == 5
        assert fc.rate is None


class TestLazyCallStepRetryDelay:
    def test_sync_step_stores_retry_delay(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 3, None,
            retry_delay="pow(2, retried) * 1000",
        )
        assert step.retry_delay == "pow(2, retried) * 1000"

    def test_sync_step_retry_delay_defaults_to_none(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 0, None,
        )
        assert step.retry_delay is None

    def test_async_step_stores_retry_delay(self) -> None:
        step = AsyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 3, None,
            retry_delay="1000",
        )
        assert step.retry_delay == "1000"


class TestLazyCallStepFlowControl:
    def test_sync_step_stores_flow_control(self) -> None:
        fc = FlowControl(key="my-key", rate=50, parallelism=10, period="1m")
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "POST", None, {}, 0, None,
            flow_control=fc,
        )
        assert step.flow_control is fc
        assert step.flow_control.key == "my-key"

    def test_sync_step_flow_control_defaults_to_none(self) -> None:
        step = SyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 0, None,
        )
        assert step.flow_control is None

    def test_async_step_stores_flow_control(self) -> None:
        fc = FlowControl(key="stripe-limiter", rate=25)
        step = AsyncLazyCallStep(
            "call-step", "https://example.com", "GET", None, {}, 0, None,
            flow_control=fc,
        )
        assert step.flow_control is fc


class TestContextCallRetryDelayAPI:
    def test_sync_call_has_retry_delay_param(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert "retry_delay" in sig.parameters

    def test_sync_call_retry_delay_default_is_none(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert sig.parameters["retry_delay"].default is None

    def test_async_call_has_retry_delay_param(self) -> None:
        sig = inspect.signature(AsyncWorkflowContext.call)
        assert "retry_delay" in sig.parameters

    def test_async_call_retry_delay_default_is_none(self) -> None:
        sig = inspect.signature(AsyncWorkflowContext.call)
        assert sig.parameters["retry_delay"].default is None


class TestContextCallFlowControlAPI:
    def test_sync_call_has_flow_control_param(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert "flow_control" in sig.parameters

    def test_sync_call_flow_control_default_is_none(self) -> None:
        sig = inspect.signature(WorkflowContext.call)
        assert sig.parameters["flow_control"].default is None

    def test_async_call_has_flow_control_param(self) -> None:
        sig = inspect.signature(AsyncWorkflowContext.call)
        assert "flow_control" in sig.parameters

    def test_async_call_flow_control_default_is_none(self) -> None:
        sig = inspect.signature(AsyncWorkflowContext.call)
        assert sig.parameters["flow_control"].default is None


class TestRetryDelayHeaderIntegration:
    @pytest.mark.asyncio
    async def test_retry_delay_sets_header(self) -> None:
        from qstash import AsyncQStash
        from aiohttp import web

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-retry-delay",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        async def capture_request(request: web.Request) -> web.Response:
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return web.json_response(
                data=[{"messageId": "msg-retry-delay", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort):
                await context.call(
                    "retry-delay-step",
                    url="https://api.example.com/data",
                    method="POST",
                    retries=3,
                    retry_delay="pow(2, retried) * 1000",
                )

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        headers = batch_item["headers"]
        assert headers["Upstash-Retry-Delay"] == "pow(2, retried) * 1000"

    @pytest.mark.asyncio
    async def test_no_retry_delay_header_when_none(self) -> None:
        from qstash import AsyncQStash
        from aiohttp import web

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-no-retry-delay",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        async def capture_request(request: web.Request) -> web.Response:
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return web.json_response(
                data=[{"messageId": "msg-no-delay", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort):
                await context.call(
                    "no-delay-step",
                    url="https://api.example.com/data",
                    method="GET",
                )

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        headers = batch_item["headers"]
        assert "Upstash-Retry-Delay" not in headers


class TestFlowControlHeaderIntegration:
    @pytest.mark.asyncio
    async def test_flow_control_sets_headers(self) -> None:
        from qstash import AsyncQStash
        from aiohttp import web

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-flow-control",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        async def capture_request(request: web.Request) -> web.Response:
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return web.json_response(
                data=[{"messageId": "msg-flow", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort):
                await context.call(
                    "flow-step",
                    url="https://api.openai.com/v1/chat",
                    method="POST",
                    body={"prompt": "hello"},
                    flow_control=FlowControl(
                        key="openai-limiter",
                        rate=50,
                        parallelism=10,
                        period="1m",
                    ),
                )

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        headers = batch_item["headers"]
        assert headers["Upstash-Flow-Control-Key"] == "openai-limiter"
        flow_value = headers["Upstash-Flow-Control-Value"]
        assert "rate=50" in flow_value
        assert "parallelism=10" in flow_value
        assert "period=1m" in flow_value

    @pytest.mark.asyncio
    async def test_flow_control_with_rate_only(self) -> None:
        from qstash import AsyncQStash
        from aiohttp import web

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-flow-rate",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        async def capture_request(request: web.Request) -> web.Response:
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return web.json_response(
                data=[{"messageId": "msg-rate", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort):
                await context.call(
                    "rate-step",
                    url="https://api.stripe.com/v1/charges",
                    method="POST",
                    flow_control=FlowControl(key="stripe-limiter", rate=100),
                )

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        headers = batch_item["headers"]
        assert headers["Upstash-Flow-Control-Key"] == "stripe-limiter"
        flow_value = headers["Upstash-Flow-Control-Value"]
        assert "rate=100" in flow_value
        assert "parallelism" not in flow_value

    @pytest.mark.asyncio
    async def test_no_flow_control_headers_when_none(self) -> None:
        from qstash import AsyncQStash
        from aiohttp import web

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-no-flow",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        async def capture_request(request: web.Request) -> web.Response:
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return web.json_response(
                data=[{"messageId": "msg-no-flow", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort):
                await context.call(
                    "no-flow-step",
                    url="https://api.example.com/data",
                    method="GET",
                )

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        headers = batch_item["headers"]
        assert "Upstash-Flow-Control-Key" not in headers
        assert "Upstash-Flow-Control-Value" not in headers


class TestSyncRetryDelayIntegration:
    def test_retry_delay_sets_header_sync(self) -> None:
        import http.server
        import socketserver
        import threading

        qstash_client = QStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = WorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-sync-retry-delay",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        class CaptureHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                request_body_captured.append(json.loads(body))
                response = json.dumps([{"messageId": "msg-sync-delay", "deduplicated": False}])
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(response.encode())

            def log_message(self, format: str, *args: object) -> None:
                pass

        class ThreadedServer(socketserver.TCPServer):
            allow_reuse_address = True

        server = ThreadedServer(("localhost", MOCK_QSTASH_SERVER_PORT), CaptureHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            with pytest.raises(WorkflowAbort):
                context.call(
                    "sync-delay-step",
                    url="https://api.example.com/data",
                    method="POST",
                    retries=5,
                    retry_delay="1000 * (1 + retried)",
                )

            assert len(request_body_captured) == 1
            batch_item = request_body_captured[0][0]
            headers = batch_item["headers"]
            assert headers["Upstash-Retry-Delay"] == "1000 * (1 + retried)"
        finally:
            server.shutdown()
            server.server_close()


class TestSyncFlowControlIntegration:
    def test_flow_control_sets_headers_sync(self) -> None:
        import http.server
        import socketserver
        import threading

        qstash_client = QStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)
        context = WorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-sync-flow",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured: list[object] = []

        class CaptureHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                request_body_captured.append(json.loads(body))
                response = json.dumps([{"messageId": "msg-sync-flow", "deduplicated": False}])
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(response.encode())

            def log_message(self, format: str, *args: object) -> None:
                pass

        class ThreadedServer(socketserver.TCPServer):
            allow_reuse_address = True

        server = ThreadedServer(("localhost", MOCK_QSTASH_SERVER_PORT), CaptureHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            with pytest.raises(WorkflowAbort):
                context.call(
                    "sync-flow-step",
                    url="https://api.openai.com/v1/chat",
                    method="POST",
                    body={"prompt": "test"},
                    flow_control=FlowControl(
                        key="openai-key",
                        parallelism=5,
                        period="30s",
                    ),
                )

            assert len(request_body_captured) == 1
            batch_item = request_body_captured[0][0]
            headers = batch_item["headers"]
            assert headers["Upstash-Flow-Control-Key"] == "openai-key"
            flow_value = headers["Upstash-Flow-Control-Value"]
            assert "parallelism=5" in flow_value
            assert "period=30s" in flow_value
            assert "rate" not in flow_value
        finally:
            server.shutdown()
            server.server_close()
