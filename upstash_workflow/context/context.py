import json
import datetime
from typing import (
    List,
    Dict,
    Union,
    Optional,
    Callable,
    TypeVar,
    Any,
    cast,
    Generic,
)
from qstash import QStash
from upstash_workflow.constants import DEFAULT_RETRIES
from upstash_workflow.context.auto_executor import _AutoExecutor
from upstash_workflow.context.steps import (
    _LazyFunctionStep,
    _LazySleepStep,
    _LazySleepUntilStep,
    _LazyCallStep,
    _LazyWaitStep,
    _LazyNotifyStep,
    _LazyInvokeStep,
    _BaseLazyStep,
)
from upstash_workflow.types import (
    DefaultStep,
    HTTPMethods,
    CallResponse,
    CallResponseDict,
    InvokeStepResponse,
    InvokableWorkflow,
    WaitForEventResult,
    NotifyResult,
)
from upstash_workflow.error import WorkflowError

TInitialPayload = TypeVar("TInitialPayload")
TResult = TypeVar("TResult")


def _derive_invoke_url(parent_url: str, workflow_id: str) -> str:
    """
    Derives the child workflow URL by replacing the last path segment
    of the parent URL with the workflow_id.
    """
    parts = parent_url.rstrip("/").rsplit("/", 1)
    return f"{parts[0]}/{workflow_id}"


class WorkflowContext(Generic[TInitialPayload]):
    """
    Upstash Workflow context

    See the docs for fields and methods https://upstash.com/docs/workflow/basics/context
    """

    def __init__(
        self,
        qstash_client: QStash,
        workflow_run_id: str,
        headers: Dict[str, str],
        steps: List[DefaultStep],
        url: str,
        failure_url: Optional[str],
        initial_payload: TInitialPayload,
        env: Optional[Dict[str, Optional[str]]] = None,
        retries: Optional[int] = None,
    ):
        self.qstash_client: QStash = qstash_client
        self.workflow_run_id: str = workflow_run_id
        self._steps: List[DefaultStep] = steps
        self.url: str = url
        self.failure_url = failure_url
        self.headers: Dict[str, str] = headers
        self.request_payload: TInitialPayload = initial_payload
        self.env: Dict[str, Optional[str]] = env or {}
        self.retries: int = DEFAULT_RETRIES if retries is None else retries
        self._executor: _AutoExecutor = _AutoExecutor(self, self._steps)

    def run(
        self,
        step_name: str,
        step_function: Union[Callable[[], Any], Callable[[], Any]],
    ) -> Any:
        """
        Executes a workflow step
        ```python
        def _step1() -> str:
            return "result"
        result = context.run("step1", _step1)
        ```

        :param step_name: name of the step
        :param step_function: step function to be executed
        :return: result of the step function
        """
        return self._add_step(_LazyFunctionStep(step_name, step_function))

    def sleep(self, step_name: str, duration: Union[int, str]) -> None:
        """
        Stops the execution for the duration provided.

        ```python
        context.sleep("sleep1", 3)  # wait for three seconds
        ```

        :param step_name: name of the step
        :param duration: sleep duration in seconds
        :return: None
        """
        self._add_step(_LazySleepStep(step_name, duration))

    def sleep_until(
        self, step_name: str, date_time: Union[datetime.datetime, str, float]
    ) -> None:
        """
        Stops the execution until the date time provided.

        ```python
        context.sleep_until("sleep1", time.time() + 3)  # wait for three seconds
        ```

        :param step_name: name of the step
        :param date_time: time to sleep until. Can be provided as a number (in unix seconds), datetime object or string in iso format
        :return: None
        """
        if isinstance(date_time, (int, float)):
            time = date_time
        elif isinstance(date_time, str):
            time = datetime.datetime.fromisoformat(date_time).timestamp()
        else:
            time = date_time.timestamp()

        self._add_step(_LazySleepUntilStep(step_name, round(time)))

    def call(
        self,
        step_name: str,
        *,
        url: str,
        method: HTTPMethods = "GET",
        body: Any = None,
        headers: Optional[Dict[str, str]] = None,
        retries: int = 0,
        timeout: Optional[Union[int, str]] = None,
    ) -> CallResponse[Any]:
        """
        Makes a third party call through QStash in order to make a network call without consuming any runtime.

        ```python
        response = context.call(
            "post-call-step",
            url="https://www.some-endpoint.com/api",
            method="POST",
            body={"message": "my-message"},
        )
        status, body, header = response.status, response.body, response.header
        ```

        tries to parse the result of the request as JSON. If it's not a JSON which can be parsed, simply returns the response body as it is.

        :param step_name: name of the step
        :param url: url to call
        :param method: call method. "GET" by default
        :param body: call body
        :param headers: call headers
        :param retries: number of call retries. 0 by default
        :param timeout: max duration to wait for the endpoint to respond. in seconds.
        :return: CallResponse object containing status, body and header
        """
        headers = headers or {}

        result = self._add_step(
            _LazyCallStep[CallResponseDict](
                step_name, url, method, body, headers, retries, timeout
            )
        )

        try:
            return CallResponse(
                status=result["status"],
                body=json.loads(result["body"]),
                header=result["header"],
            )
        except Exception:
            return cast(CallResponse[Any], result)

    def wait_for_event(
        self,
        step_name: str,
        event_id: str,
        *,
        timeout: Optional[Union[int, str]] = None,
    ) -> WaitForEventResult:
        """
        Pauses workflow execution and waits for an external event.

        When the workflow reaches this step, it exits but stores a waiter.
        When `notify()` is called with the same event_id, the workflow
        resumes with the provided event data.

        ```python
        result = context.wait_for_event("wait-for-approval", "approval-123", timeout="7d")
        if result.timeout:
            # Handle timeout
            pass
        else:
            # Use result.event_data
            pass
        ```

        :param step_name: name of the step
        :param event_id: unique identifier for the event to wait for
        :param timeout: maximum time to wait (e.g., "7d", "1h", 300). Defaults to "7d"
        :return: WaitForEventResult with event_data and timeout flag
        """
        return self._add_step(_LazyWaitStep(step_name, event_id, timeout))

    def notify(
        self,
        step_name: str,
        event_id: str,
        event_data: Any = None,
    ) -> NotifyResult:
        """
        Notifies workflows waiting for the specified event.

        This will resume any workflows that are waiting for this event_id
        via `wait_for_event()`.

        ```python
        result = context.notify("notify-approval", "approval-123", {"approved": True})
        print(f"Notified {result.notified_count} workflows")
        ```

        :param step_name: name of the step
        :param event_id: unique identifier for the event to notify
        :param event_data: data to pass to waiting workflows
        :return: NotifyResult with event_id and notified_count
        """
        return self._add_step(_LazyNotifyStep(step_name, event_id, event_data))

    def invoke(
        self,
        step_name: str,
        *,
        workflow: InvokableWorkflow,
        body: Any = None,
        headers: Optional[Dict[str, str]] = None,
        retries: Optional[int] = None,
    ) -> InvokeStepResponse[Any]:
        """
        Invokes another workflow registered via serve_many and waits for its result.

        ```python
        child_workflow = create_workflow(my_child_fn)

        result = context.invoke(
            "invoke-child",
            workflow=child_workflow,
            body={"key": "value"},
        )
        print(result.body)        # result from child workflow
        print(result.is_failed)   # True if child workflow failed
        print(result.is_canceled) # True if child workflow was canceled
        ```

        :param step_name: name of the step
        :param workflow: InvokableWorkflow to invoke (must be registered via serve_many)
        :param body: payload to send to the invoked workflow
        :param headers: optional headers to forward
        :param retries: number of retries
        :return: InvokeStepResponse with body, is_failed, is_canceled
        """
        if not workflow.workflow_id:
            raise WorkflowError(
                "Workflow does not have a workflow_id. "
                "Make sure to register it with serve_many before invoking."
            )

        invoke_url = _derive_invoke_url(self.url, workflow.workflow_id)

        result = self._add_step(
            _LazyInvokeStep(
                step_name,
                url=invoke_url,
                body=body,
                headers=headers,
                retries=retries,
            )
        )

        try:
            if isinstance(result, dict):
                return InvokeStepResponse(
                    body=json.loads(result["body"])
                    if isinstance(result.get("body"), str)
                    else result.get("body"),
                    is_failed=result.get("is_failed", False),
                    is_canceled=result.get("is_canceled", False),
                )
            return InvokeStepResponse(body=result)
        except Exception:
            return InvokeStepResponse(body=result)

    def _add_step(self, step: _BaseLazyStep[TResult]) -> TResult:
        """
        Adds steps to the executor. Needed so that it can be overwritten in
        DisabledWorkflowContext.
        """
        return self._executor.add_step(step)
