"""Main class for pCloud API client access."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp.multipart import MultipartWriter
from aiohttp.payload import AsyncIterablePayload
from multidict import MultiDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator

    from .auth import AbstractAuth

BASE_API_URL = "https://api.pcloud.com"


class PCloudApiError(Exception):
    """Raised when pCloud API returns an error."""

    def __init__(self, obj: object) -> None:
        """Initialize custom Error."""
        super().__init__(obj)
        self.code = None
        if isinstance(obj, dict):
            self.code = obj.get("result")
            self.msg = obj.get("error")
        if self.code is None:
            self.code = "unexpected error"
            self.msg = str(obj)

    def __str__(self) -> str:
        """Return formatted error message."""
        return f"{self.code}: {self.msg}"


class Client:
    """Async client for pCloud API."""

    def __init__(self, auth: AbstractAuth) -> None:
        """Initialize client with auth for autheticated requests."""
        self._auth = auth

    async def basic_req(self, method: str, **parameters: str | int) -> Any:
        """Make a basic request to the pCloud API.

        See https://docs.pcloud.com/ for full documentation
        This works only for "normal" API methods with parameters and JSON resonse.
        There are special functions for file up-/download
        Infos:
            - Example path to file: "/folder/file.ext"
            - Example path to folder: "/folder" (no trailing slash)

        Args:
            method (str): API method
            parameters (str|int): Parameters for the method

        Raises:
            PCloudApiError: Raised if the response has a non-zero error code ("result")

        Returns:
            Any: the decode JSON respons. The response depends on the API method,
                 see documentation for example responses.

        """
        response = await self._auth._request("GET", method, params=parameters)
        output = await response.json()

        if output.get("result") != 0:
            raise PCloudApiError(output)
        return output

    async def upload_file_iter(
        self,
        *,
        filename: str,
        size: int,
        data: AsyncIterator[bytes],
        **parameters: str | int,
    ) -> Any:
        """Upload a file from a AsyncIterator.

        The pCloud server doesn't seem to accept or understand chunked uploads,
        therefor the size of the data has to be given exactly in bytes.

        See https://docs.pcloud.com/methods/file/uploadfile.html for accepted
        parameters and example response.

        Args:
            filename (str): Filename for the uploaded file
            size (int): size of the file in bytes
            data (AsyncIterator[bytes]): asynch Iterator providing the data
            parameters (str|int): Additional parameters.
                At least path or folderid should be given (defaults to root folder if omitted)

        Raises:
            PCloudApiError: Raised if the response has a non-zero error code ("result")

        Returns:
            Any: the decode JSON respons. See documentation for example response.

        """

        class SizedAsyncIterablePayload(AsyncIterablePayload):
            def __init__(self, size: int, value: AsyncIterable, *args: Any, **kwargs: Any) -> None:
                self._size = size
                super().__init__(value, *args, **kwargs)

        mdict = MultiDict({"name": "files"})
        mdict["filename"] = filename
        payload = SizedAsyncIterablePayload(size, data)
        payload.set_content_disposition("form-data", quote_fields=True, **mdict)

        mpwriter = MultipartWriter("form-data")
        mpwriter.append(payload)

        response = await self._auth._request(
            "POST",
            "uploadfile",
            params=parameters,
            data=mpwriter,
            timeout=aiohttp.ClientTimeout(total=15),
        )
        output = await response.json()

        if output.get("result") != 0:
            raise PCloudApiError(output)
        return output

    async def download_file_iter(
        self,
        fileid: int | None = None,
        path: str | None = None,
    ) -> AsyncIterator[bytes]:
        """Download a file an return a AsyncIterator.

        Args:
            fileid (int | None, optional): ID of the file to download. Defaults to None.
            path (str | None, optional): Name of the file to download. Defaults to None.

        Raises:
            PCloudApiError: Raised if the response has a non-zero error code ("result")

        Returns:
            AsyncIterator[bytes]: Async generator providing the download data

        """
        args = {}
        args["forcedownload"] = 1
        if fileid is not None:
            args["fileid"] = fileid
        elif path is not None:
            args["path"] = path

        response = await self._auth._request("GET", "getfilelink", params=args)
        output = await response.json()
        if output.get("result") != 0:
            raise PCloudApiError(output)

        filelink = f"https://{output.get('hosts')[0]}{output.get('path')}"

        response = await self._auth._request_raw("GET", filelink)
        return (chunk async for chunk, _ in response.content.iter_chunks())
