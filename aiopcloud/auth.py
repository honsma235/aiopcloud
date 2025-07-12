"""Auth class for pCloud API client access."""

from abc import ABC, abstractmethod
from typing import Any

from aiohttp import ClientResponse, ClientSession


class AbstractAuth(ABC):
    """Abstract class to make authenticated requests."""

    def __init__(self, websession: ClientSession, hostname: str) -> None:
        """Initialize the auth."""
        self._websession: ClientSession = websession
        self._hostname: str = hostname

    @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""

    async def _request(self, method: str, path: str, **kwargs: Any) -> ClientResponse:
        return await self._request_raw(
            method=method,
            url=f"https://{self._hostname}/{path}",
            **kwargs,
        )

    async def _request_raw(self, method: str, url: str, **kwargs: Any) -> ClientResponse:
        if headers := kwargs.pop("headers", {}):
            headers = dict(headers)

        access_token = await self.async_get_access_token()
        headers["authorization"] = f"Bearer {access_token}"

        response: ClientResponse = await self._websession.request(
            method=method,
            url=url,
            headers=headers,
            **kwargs,
        )
        response.raise_for_status()
        return response
