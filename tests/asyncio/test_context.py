import pytest
from qstash import AsyncQStash
from upstash_workflow import AsyncWorkflowContext
from upstash_workflow.error import WorkflowAbort
from tests.utils import (
    RequestFields,
    ResponseFields,
    MOCK_QSTASH_SERVER_URL,
    WORKFLOW_ENDPOINT,
)
from tests.asyncio.utils import mock_qstash_server


@pytest.fixture
def qstash_client() -> AsyncQStash:
    return AsyncQStash("mock-token", base_url=MOCK_QSTASH_SERVER_URL)


@pytest.mark.asyncio
async def test_workflow_headers(qstash_client: AsyncQStash) -> None:
    url = "https://some-website.com"
    body = "request-body"
    retries = 10

    context = AsyncWorkflowContext(
        qstash_client=qstash_client,
        workflow_run_id="wfr-id",
        headers={},
        steps=[],
        url=WORKFLOW_ENDPOINT,
        initial_payload="my-payload",
        env=None,
        retries=1,
        failure_url=WORKFLOW_ENDPOINT,
    )

    async def execute() -> None:
        with pytest.raises(WorkflowAbort) as excinfo:
            await context.call(
                "my-step",
                url=url,
                method="PATCH",
                body=body,
                headers={"my-header": "my-value"},
                retries=retries,
            )

        assert "Aborting workflow after executing step 'my-step'." in str(excinfo.value)

    await mock_qstash_server(
        execute=execute,
        response_fields=ResponseFields(status=200, body="msgId"),
        receives_request=RequestFields(
            method="POST",
            url=f"{MOCK_QSTASH_SERVER_URL}/v2/batch",
            token="mock-token",
            body=[
                {
                    "body": '"request-body"',
                    "destination": url,
                    "queue": None,
                    "headers": {
                        "Content-Type": "application/json",
                        "Upstash-Method": "PATCH",
                        "Upstash-Forward-Upstash-Workflow-Init": "false",
                        "Upstash-Forward-Upstash-Workflow-RunId": "wfr-id",
                        "Upstash-Forward-Upstash-Workflow-Url": "https://www.my-website.com/api",
                        "Upstash-Forward-Upstash-Feature-Set": "WF_NoDelete,InitialBody",
                        "Upstash-Forward-Upstash-Failure-Callback-Forward-Upstash-Workflow-Is-Failure": "true",
                        "Upstash-Forward-Upstash-Failure-Callback-Forward-Upstash-Workflow-Failure-Callback": "true",
                        "Upstash-Forward-Upstash-Failure-Callback-Workflow-Runid": "wfr-id",
                        "Upstash-Forward-Upstash-Failure-Callback-Workflow-Init": "false",
                        "Upstash-Forward-Upstash-Failure-Callback-Workflow-Url": "https://www.my-website.com/api",
                        "Upstash-Forward-Upstash-Failure-Callback-Workflow-Calltype": "failureCall",
                        "Upstash-Forward-Upstash-Failure-Callback-Feature-Set": "LazyFetch,InitialBody",
                        "Upstash-Forward-Upstash-Callback-Failure-Callback-Forward-Upstash-Workflow-Is-Failure": "true",
                        "Upstash-Forward-Upstash-Callback-Failure-Callback-Forward-Upstash-Workflow-Failure-Callback": "true",
                        "Upstash-Forward-Upstash-Callback-Failure-Callback-Workflow-Runid": "wfr-id",
                        "Upstash-Forward-Upstash-Callback-Failure-Callback-Workflow-Init": "false",
                        "Upstash-Forward-Upstash-Callback-Failure-Callback-Workflow-Url": "https://www.my-website.com/api",
                        "Upstash-Forward-Upstash-Callback-Failure-Callback-Workflow-Calltype": "failureCall",
                        "Upstash-Forward-Upstash-Callback-Failure-Callback-Feature-Set": "LazyFetch,InitialBody",
                        "Upstash-Forward-Upstash-Failure-Callback-Retries": "1",
                        "Upstash-Forward-Upstash-Callback-Failure-Callback-Retries": "1",
                        "Upstash-Forward-Upstash-Retries": "10",
                        "Upstash-Forward-Upstash-Callback-Retries": "1",
                        "Upstash-Forward-my-header": "my-value",
                        "Upstash-Forward-Upstash-Callback": "https://www.my-website.com/api",
                        "Upstash-Forward-Upstash-Callback-Workflow-RunId": "wfr-id",
                        "Upstash-Forward-Upstash-Callback-Workflow-CallType": "fromCallback",
                        "Upstash-Forward-Upstash-Callback-Workflow-Init": "false",
                        "Upstash-Forward-Upstash-Callback-Workflow-Url": "https://www.my-website.com/api",
                        "Upstash-Forward-Upstash-Callback-Feature-Set": "LazyFetch,InitialBody",
                        "Upstash-Forward-Upstash-Callback-Forward-Upstash-Workflow-Callback": "true",
                        "Upstash-Forward-Upstash-Callback-Forward-Upstash-Workflow-StepId": "1",
                        "Upstash-Forward-Upstash-Callback-Forward-Upstash-Workflow-StepName": "my-step",
                        "Upstash-Forward-Upstash-Callback-Forward-Upstash-Workflow-StepType": "Call",
                        "Upstash-Forward-Upstash-Callback-Forward-Upstash-Workflow-Concurrent": "1",
                        "Upstash-Forward-Upstash-Callback-Forward-Upstash-Workflow-ContentType": "application/json",
                        "Upstash-Forward-Upstash-Workflow-CallType": "toCallback",
                    },
                }
            ],
        ),
    )
