import json
from typing import Any, List, Optional
import httpx
from upstash_workflow.types import NotifyResponse


DEFAULT_BASE_URL = "https://qstash.upstash.io"


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
    ) -> List[NotifyResponse]:
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

        return [
            NotifyResponse(
                message_id=item.get("messageId", ""),
                waiter_url=item.get("waiter", {}).get("url", ""),
                waiter_deadline=item.get("waiter", {}).get("deadline", 0),
            )
            for item in data
        ]


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
    ) -> List[NotifyResponse]:
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

        return [
            NotifyResponse(
                message_id=item.get("messageId", ""),
                waiter_url=item.get("waiter", {}).get("url", ""),
                waiter_deadline=item.get("waiter", {}).get("deadline", 0),
            )
            for item in data
        ]
