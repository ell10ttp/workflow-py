import pytest
from dataclasses import is_dataclass


class TestStepDataclassExtensions:
    def test_step_has_wait_event_id_field(self) -> None:
        from upstash_workflow.types import Step

        step = Step(
            step_id=1,
            step_name="wait-step",
            step_type="Wait",
            concurrent=1,
            wait_event_id="my-event-id",
        )
        assert step.wait_event_id == "my-event-id"

    def test_step_has_wait_timeout_field(self) -> None:
        from upstash_workflow.types import Step

        step = Step(
            step_id=1,
            step_name="wait-step",
            step_type="Wait",
            concurrent=1,
            wait_timeout="7d",
        )
        assert step.wait_timeout == "7d"


class TestWaitForEventResultType:
    def test_wait_for_event_result_is_dataclass(self) -> None:
        from upstash_workflow.types import WaitForEventResult

        assert is_dataclass(WaitForEventResult)

    def test_wait_for_event_result_has_event_data_field(self) -> None:
        from upstash_workflow.types import WaitForEventResult

        result = WaitForEventResult(event_data={"key": "value"}, timeout=False)
        assert result.event_data == {"key": "value"}

    def test_wait_for_event_result_has_timeout_field(self) -> None:
        from upstash_workflow.types import WaitForEventResult

        result = WaitForEventResult(event_data=None, timeout=True)
        assert result.timeout is True

    def test_wait_for_event_result_event_data_can_be_none(self) -> None:
        from upstash_workflow.types import WaitForEventResult

        result = WaitForEventResult(event_data=None, timeout=True)
        assert result.event_data is None


class TestNotifyResultType:
    def test_notify_result_is_dataclass(self) -> None:
        from upstash_workflow.types import NotifyResult

        assert is_dataclass(NotifyResult)

    def test_notify_result_has_event_id_field(self) -> None:
        from upstash_workflow.types import NotifyResult

        result = NotifyResult(event_id="my-event", notified_count=3)
        assert result.event_id == "my-event"

    def test_notify_result_has_notified_count_field(self) -> None:
        from upstash_workflow.types import NotifyResult

        result = NotifyResult(event_id="my-event", notified_count=5)
        assert result.notified_count == 5


class TestLazyWaitStep:
    def test_lazy_wait_step_can_be_imported(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyWaitStep

        assert _LazyWaitStep is not None

    def test_lazy_wait_step_has_wait_step_type(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyWaitStep

        step = _LazyWaitStep("wait-step", "event-123", timeout="7d")
        assert step.step_type == "Wait"

    def test_lazy_wait_step_stores_event_id(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyWaitStep

        step = _LazyWaitStep("wait-step", "my-event-id", timeout=None)
        assert step.event_id == "my-event-id"

    def test_lazy_wait_step_stores_timeout(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyWaitStep

        step = _LazyWaitStep("wait-step", "event-id", timeout="30s")
        assert step.timeout == "30s"

    def test_lazy_wait_step_timeout_defaults_to_7d(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyWaitStep

        step = _LazyWaitStep("wait-step", "event-id", timeout=None)
        assert step.timeout == "7d"

    def test_lazy_wait_step_converts_int_timeout_to_string(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyWaitStep

        step = _LazyWaitStep("wait-step", "event-id", timeout=300)
        assert step.timeout == "300s"

    def test_lazy_wait_step_get_plan_step_includes_wait_event_id(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyWaitStep

        step = _LazyWaitStep("wait-step", "my-event-id", timeout="7d")
        plan_step = step.get_plan_step(concurrent=1, target_step=0)

        assert plan_step.wait_event_id == "my-event-id"
        assert plan_step.step_type == "Wait"

    def test_lazy_wait_step_get_plan_step_includes_wait_timeout(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyWaitStep

        step = _LazyWaitStep("wait-step", "event-id", timeout="1h")
        plan_step = step.get_plan_step(concurrent=1, target_step=0)

        assert plan_step.wait_timeout == "1h"

    @pytest.mark.asyncio
    async def test_lazy_wait_step_get_result_step_includes_wait_fields(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyWaitStep

        step = _LazyWaitStep("wait-step", "my-event", timeout="5m")
        result_step = await step.get_result_step(concurrent=1, step_id=5)

        assert result_step.wait_event_id == "my-event"
        assert result_step.wait_timeout == "5m"
        assert result_step.step_id == 5
        assert result_step.step_type == "Wait"


class TestLazyNotifyStep:
    def test_lazy_notify_step_can_be_imported(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyNotifyStep

        assert _LazyNotifyStep is not None

    def test_lazy_notify_step_has_notify_step_type(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyNotifyStep

        step = _LazyNotifyStep("notify-step", "event-123", event_data={"key": "value"})
        assert step.step_type == "Notify"

    def test_lazy_notify_step_stores_event_id(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyNotifyStep

        step = _LazyNotifyStep("notify-step", "my-event-id", event_data=None)
        assert step.event_id == "my-event-id"

    def test_lazy_notify_step_stores_event_data(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyNotifyStep

        data = {"user_id": 123, "action": "approved"}
        step = _LazyNotifyStep("notify-step", "event-id", event_data=data)
        assert step.event_data == data

    def test_lazy_notify_step_event_data_can_be_none(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyNotifyStep

        step = _LazyNotifyStep("notify-step", "event-id", event_data=None)
        assert step.event_data is None

    def test_lazy_notify_step_get_plan_step_has_correct_type(self) -> None:
        from upstash_workflow.asyncio.context.steps import _LazyNotifyStep

        step = _LazyNotifyStep("notify-step", "event-id", event_data={"key": "val"})
        plan_step = step.get_plan_step(concurrent=1, target_step=0)

        assert plan_step.step_type == "Notify"
        assert plan_step.step_name == "notify-step"


class TestContextWaitForEvent:
    def test_context_has_wait_for_event_method(self) -> None:
        from upstash_workflow import AsyncWorkflowContext

        assert hasattr(AsyncWorkflowContext, "wait_for_event")
        assert callable(getattr(AsyncWorkflowContext, "wait_for_event"))

    def test_wait_for_event_accepts_step_name_and_event_id(self) -> None:
        import inspect
        from upstash_workflow import AsyncWorkflowContext

        sig = inspect.signature(AsyncWorkflowContext.wait_for_event)
        params = list(sig.parameters.keys())

        assert "step_name" in params
        assert "event_id" in params

    def test_wait_for_event_accepts_optional_timeout(self) -> None:
        import inspect
        from upstash_workflow import AsyncWorkflowContext

        sig = inspect.signature(AsyncWorkflowContext.wait_for_event)
        params = sig.parameters

        assert "timeout" in params
        assert params["timeout"].default is None


class TestContextNotify:
    def test_context_has_notify_method(self) -> None:
        from upstash_workflow import AsyncWorkflowContext

        assert hasattr(AsyncWorkflowContext, "notify")
        assert callable(getattr(AsyncWorkflowContext, "notify"))

    def test_notify_accepts_step_name_event_id_and_data(self) -> None:
        import inspect
        from upstash_workflow import AsyncWorkflowContext

        sig = inspect.signature(AsyncWorkflowContext.notify)
        params = list(sig.parameters.keys())

        assert "step_name" in params
        assert "event_id" in params
        assert "event_data" in params


class TestAutoExecutorWaitStep:
    @pytest.mark.asyncio
    async def test_wait_step_body_includes_wait_event_id(self) -> None:
        from qstash import AsyncQStash
        from upstash_workflow import AsyncWorkflowContext
        from upstash_workflow.error import WorkflowAbort
        from tests.utils import MOCK_QSTASH_SERVER_URL, WORKFLOW_ENDPOINT
        from tests.asyncio.utils import mock_qstash_server
        import json

        qstash_client = AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)

        context = AsyncWorkflowContext(
            qstash_client=qstash_client,
            workflow_run_id="wfr-test",
            headers={},
            steps=[],
            url=WORKFLOW_ENDPOINT,
            initial_payload="payload",
            env=None,
            retries=1,
            failure_url=WORKFLOW_ENDPOINT,
        )

        request_body_captured = []

        async def capture_request_body(request):
            import aiohttp
            text = await request.text()
            request_body_captured.append(json.loads(text))
            return aiohttp.web.json_response(
                data=[{"messageId": "msg-123", "deduplicated": False}],
                status=200,
            )

        async def execute() -> None:
            with pytest.raises(WorkflowAbort):
                await context.wait_for_event("wait-step", "my-event-123", timeout="7d")

        from aiohttp import web

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", capture_request_body)

        runner = web.AppRunner(app)
        await runner.setup()
        from tests.utils import MOCK_QSTASH_SERVER_PORT
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            await execute()
        finally:
            await runner.cleanup()

        assert len(request_body_captured) == 1
        batch_item = request_body_captured[0][0]
        body = batch_item["body"]
        if isinstance(body, str):
            import json as json_mod
            body = json_mod.loads(body)
        assert body["waitEventId"] == "my-event-123"
        assert body["waitTimeout"] == "7d"
        assert body["stepType"] == "Wait"


class TestClientClass:
    def test_client_can_be_imported(self) -> None:
        from upstash_workflow import Client

        assert Client is not None

    def test_client_has_notify_method(self) -> None:
        from upstash_workflow import Client

        assert hasattr(Client, "notify")
        assert callable(getattr(Client, "notify"))

    def test_client_accepts_token_parameter(self) -> None:
        from upstash_workflow import Client

        client = Client(token="test-token")
        assert client is not None

    def test_client_accepts_optional_base_url(self) -> None:
        from upstash_workflow import Client

        client = Client(token="test-token", base_url="https://custom.qstash.io")
        assert client._base_url == "https://custom.qstash.io"

    def test_client_default_base_url(self) -> None:
        from upstash_workflow import Client

        client = Client(token="test-token")
        assert client._base_url == "https://qstash.upstash.io"


class TestSyncClientNotify:
    def test_sync_client_notify_calls_correct_endpoint(self) -> None:
        from upstash_workflow import Client
        from tests.utils import MOCK_QSTASH_SERVER_URL, MOCK_QSTASH_SERVER_PORT
        import http.server
        import socketserver
        import threading
        import json

        request_captured: dict = {}

        class CaptureHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                request_captured["method"] = self.command
                request_captured["path"] = self.path
                content_length = int(self.headers.get("Content-Length", 0))
                request_captured["body"] = self.rfile.read(content_length).decode()
                request_captured["auth"] = self.headers.get("Authorization")

                response = json.dumps([
                    {
                        "waiter": {
                            "url": "https://example.com/workflow",
                            "deadline": 1234567890,
                        },
                        "messageId": "msg-sync-123",
                    }
                ])
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(response.encode())

            def log_message(self, format, *args) -> None:
                pass

        class ThreadedServer(socketserver.TCPServer):
            allow_reuse_address = True

        server = ThreadedServer(("localhost", MOCK_QSTASH_SERVER_PORT), CaptureHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            client = Client(token="test-token", base_url=MOCK_QSTASH_SERVER_URL)
            result = client.notify("my-event-id", event_data={"approved": True})

            assert request_captured["method"] == "POST"
            assert request_captured["path"] == "/v2/notify/my-event-id"
            assert request_captured["auth"] == "Bearer test-token"
            assert json.loads(request_captured["body"]) == {"approved": True}

            assert len(result) == 1
            assert result[0].message_id == "msg-sync-123"
        finally:
            server.shutdown()
            server.server_close()

    def test_sync_client_notify_with_string_data(self) -> None:
        from upstash_workflow import Client
        from tests.utils import MOCK_QSTASH_SERVER_URL, MOCK_QSTASH_SERVER_PORT
        import http.server
        import socketserver
        import threading
        import json

        request_captured: dict = {}

        class CaptureHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", 0))
                request_captured["body"] = self.rfile.read(content_length).decode()

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"[]")

            def log_message(self, format, *args) -> None:
                pass

        class ThreadedServer(socketserver.TCPServer):
            allow_reuse_address = True

        server = ThreadedServer(("localhost", MOCK_QSTASH_SERVER_PORT), CaptureHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            client = Client(token="test-token", base_url=MOCK_QSTASH_SERVER_URL)
            client.notify("event-id", event_data="plain string data")

            assert request_captured["body"] == "plain string data"
        finally:
            server.shutdown()
            server.server_close()

    def test_sync_client_notify_returns_empty_list_when_no_waiters(self) -> None:
        from upstash_workflow import Client
        from tests.utils import MOCK_QSTASH_SERVER_URL, MOCK_QSTASH_SERVER_PORT
        import http.server
        import socketserver
        import threading

        class EmptyHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"[]")

            def log_message(self, format, *args) -> None:
                pass

        class ThreadedServer(socketserver.TCPServer):
            allow_reuse_address = True

        server = ThreadedServer(("localhost", MOCK_QSTASH_SERVER_PORT), EmptyHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            client = Client(token="test-token", base_url=MOCK_QSTASH_SERVER_URL)
            result = client.notify("no-waiters-event")

            assert result == []
        finally:
            server.shutdown()
            server.server_close()


class TestAsyncClientClass:
    def test_async_client_can_be_imported(self) -> None:
        from upstash_workflow import AsyncClient

        assert AsyncClient is not None

    def test_async_client_has_notify_method(self) -> None:
        from upstash_workflow import AsyncClient

        assert hasattr(AsyncClient, "notify")
        assert callable(getattr(AsyncClient, "notify"))

    @pytest.mark.asyncio
    async def test_async_client_notify_calls_correct_endpoint(self) -> None:
        from upstash_workflow import AsyncClient
        from upstash_workflow.types import NotifyResponse
        from tests.utils import MOCK_QSTASH_SERVER_URL, MOCK_QSTASH_SERVER_PORT
        from aiohttp import web
        import json

        request_captured = {}

        async def capture_notify_request(request):
            request_captured["method"] = request.method
            request_captured["path"] = request.path
            request_captured["body"] = await request.text()
            request_captured["auth"] = request.headers.get("Authorization")
            return web.json_response(
                data=[
                    {
                        "waiter": {
                            "url": "https://example.com/workflow",
                            "deadline": 1234567890,
                        },
                        "messageId": "msg-abc123",
                    }
                ],
                status=200,
            )

        app = web.Application()
        app.router.add_route("POST", "/v2/notify/{event_id}", capture_notify_request)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            client = AsyncClient(token="test-token", base_url=MOCK_QSTASH_SERVER_URL)
            result = await client.notify("my-event-id", event_data={"approved": True})

            assert request_captured["method"] == "POST"
            assert request_captured["path"] == "/v2/notify/my-event-id"
            assert request_captured["auth"] == "Bearer test-token"
            assert json.loads(request_captured["body"]) == {"approved": True}

            assert len(result) == 1
            assert result[0].message_id == "msg-abc123"
        finally:
            await runner.cleanup()

    @pytest.mark.asyncio
    async def test_async_client_notify_with_string_data(self) -> None:
        from upstash_workflow import AsyncClient
        from tests.utils import MOCK_QSTASH_SERVER_URL, MOCK_QSTASH_SERVER_PORT
        from aiohttp import web

        request_captured = {}

        async def capture_notify_request(request):
            request_captured["body"] = await request.text()
            return web.json_response(data=[], status=200)

        app = web.Application()
        app.router.add_route("POST", "/v2/notify/{event_id}", capture_notify_request)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            client = AsyncClient(token="test-token", base_url=MOCK_QSTASH_SERVER_URL)
            await client.notify("event-id", event_data="plain string data")

            assert request_captured["body"] == "plain string data"
        finally:
            await runner.cleanup()

    @pytest.mark.asyncio
    async def test_async_client_notify_returns_empty_list_when_no_waiters(self) -> None:
        from upstash_workflow import AsyncClient
        from tests.utils import MOCK_QSTASH_SERVER_URL, MOCK_QSTASH_SERVER_PORT
        from aiohttp import web

        async def empty_response(request):
            return web.json_response(data=[], status=200)

        app = web.Application()
        app.router.add_route("POST", "/v2/notify/{event_id}", empty_response)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", MOCK_QSTASH_SERVER_PORT)

        try:
            await site.start()
            client = AsyncClient(token="test-token", base_url=MOCK_QSTASH_SERVER_URL)
            result = await client.notify("no-waiters-event")

            assert result == []
        finally:
            await runner.cleanup()
