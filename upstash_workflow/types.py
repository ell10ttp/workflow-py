from typing import (
    Callable,
    Literal,
    Optional,
    Dict,
    Union,
    List,
    TypeVar,
    Generic,
    Any,
    TypedDict,
)
from dataclasses import dataclass

_FinishCondition = Literal[
    "success",
    "duplicate-step",
    "fromCallback",
    "auth-fail",
    "failure-callback",
]

TInitialPayload = TypeVar("TInitialPayload")
TResponse = TypeVar("TResponse")


StepTypes = [
    "Initial",
    "Run",
    "SleepFor",
    "SleepUntil",
    "Call",
    "Wait",
    "Notify",
    "Invoke",
]

StepType = Literal[
    "Initial",
    "Run",
    "SleepFor",
    "SleepUntil",
    "Call",
    "Wait",
    "Notify",
    "Invoke",
]

HTTPMethods = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]


TResult = TypeVar("TResult")
TBody = TypeVar("TBody")


@dataclass
class Step(Generic[TResult, TBody]):
    step_id: int
    step_name: str
    step_type: StepType
    concurrent: int

    out: Optional[TResult] = None
    sleep_for: Optional[Union[int, str]] = None
    sleep_until: Optional[int] = None
    target_step: Optional[int] = None

    call_method: Optional[HTTPMethods] = None
    call_body: Optional[TBody] = None
    call_headers: Optional[Dict[str, str]] = None
    call_url: Optional[str] = None

    wait_event_id: Optional[str] = None
    wait_timeout: Optional[str] = None

    invoke_url: Optional[str] = None
    invoke_body: Optional[Any] = None
    invoke_headers: Optional[Dict[str, str]] = None


DefaultStep = Step[Any, Any]


@dataclass
class _ValidateRequestResponse:
    is_first_invocation: bool
    workflow_run_id: str


@dataclass
class _ParseRequestResponse:
    raw_initial_payload: str
    steps: List[DefaultStep]


@dataclass
class _HeadersResponse:
    headers: Dict[str, str]
    timeout_headers: Optional[Dict[str, List[str]]] = None


@dataclass
class CallResponse(Generic[TResult]):
    status: int
    body: TResult
    header: Dict[str, List[str]]


class CallResponseDict(TypedDict):
    status: int
    body: Any
    header: Dict[str, List[str]]


@dataclass
class WaitForEventResult:
    event_data: Optional[Any]
    timeout: bool


@dataclass
class NotifyResult:
    event_id: str
    notified_count: int


@dataclass
class InvokeStepResponse(Generic[TResult]):
    body: TResult
    is_failed: bool = False
    is_canceled: bool = False


@dataclass
class InvokableWorkflow:
    route_function: Any
    workflow_id: Optional[str] = None


@dataclass
class NotifyResponse:
    message_id: str
    waiter_url: str
    waiter_deadline: int


def create_workflow(
    route_function: Callable[..., None],
) -> InvokableWorkflow:
    """
    Wraps a sync workflow route function into an InvokableWorkflow
    that can be registered with serve_many and invoked by other workflows.

    :param route_function: A sync function that uses WorkflowContext as a parameter
    :return: An InvokableWorkflow instance
    """
    return InvokableWorkflow(route_function=route_function)


def create_async_workflow(
    route_function: Callable[..., Any],
) -> InvokableWorkflow:
    """
    Wraps an async workflow route function into an InvokableWorkflow
    that can be registered with serve_many and invoked by other workflows.

    :param route_function: An async function that uses AsyncWorkflowContext as a parameter
    :return: An InvokableWorkflow instance
    """
    return InvokableWorkflow(route_function=route_function)
