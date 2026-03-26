import json
from typing import Any, Dict, List, Optional
import httpx
from upstash_workflow.types import NotifyResponse, Waiter


DEFAULT_BASE_URL = "https://qstash.upstash.io"


def _parse_waiter(data: Dict[str, Any]) -> Waiter:
    return Waiter(
        url=data.get("url", ""),
        deadline=data.get("deadline", 0),
        headers=data.get("headers", {}),
        timeout_url=data.get("timeoutUrl"),
        timeout_body=data.get("timeoutBody"),
        timeout_headers=data.get("timeoutHeaders"),
    )


def _parse_notify_response(item: Dict[str, Any]) -> NotifyResponse:
    return NotifyResponse(
        waiter=_parse_waiter(item.get("waiter", {})),
        message_id=item.get("messageId", ""),
        error=item.get("error", ""),
    )


class Client:
    def __init__(
        self,
        token: str,
        base_url: Optional[str] = None,
    ):
        self._token = token
        self._base_url = base_url or DEFAULT_BASE_URL

    def notify(
        self,
        event_id: str,
        event_data: Any = None,
        workflow_run_id: Optional[str] = None,
    ) -> List[NotifyResponse]:
        if workflow_run_id:
            url = f"{self._base_url}/v2/notify/{workflow_run_id}/{event_id}"
        else:
            url = f"{self._base_url}/v2/notify/{event_id}"

        headers = {
            "Authorization": f"Bearer {self._token}",
        }

        if isinstance(event_data, str):
            body = event_data
        elif event_data is not None:
            body = json.dumps(event_data)
        else:
            body = None

        with httpx.Client() as client:
            response = client.post(url, headers=headers, content=body)
            response.raise_for_status()
            data = response.json()

        return [_parse_notify_response(item) for item in data]

    def get_waiters(self, event_id: str) -> List[Waiter]:
        url = f"{self._base_url}/v2/waiters/{event_id}"
        headers = {
            "Authorization": f"Bearer {self._token}",
        }

        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        return [_parse_waiter(item) for item in data]


class AsyncClient:
    def __init__(
        self,
        token: str,
        base_url: Optional[str] = None,
    ):
        self._token = token
        self._base_url = base_url or DEFAULT_BASE_URL

    async def notify(
        self,
        event_id: str,
        event_data: Any = None,
        workflow_run_id: Optional[str] = None,
    ) -> List[NotifyResponse]:
        if workflow_run_id:
            url = f"{self._base_url}/v2/notify/{workflow_run_id}/{event_id}"
        else:
            url = f"{self._base_url}/v2/notify/{event_id}"

        headers = {
            "Authorization": f"Bearer {self._token}",
        }

        if isinstance(event_data, str):
            body = event_data
        elif event_data is not None:
            body = json.dumps(event_data)
        else:
            body = None

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, content=body)
            response.raise_for_status()
            data = response.json()

        return [_parse_notify_response(item) for item in data]

    async def get_waiters(self, event_id: str) -> List[Waiter]:
        url = f"{self._base_url}/v2/waiters/{event_id}"
        headers = {
            "Authorization": f"Bearer {self._token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        return [_parse_waiter(item) for item in data]
