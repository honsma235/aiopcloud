from collections.abc import AsyncGenerator
from typing import Any

import aiohttp
import aioresponses
import pytest

import aiopcloud
from tests import const, load_fixture_bytes, load_fixture_json


@pytest.mark.asyncio
async def test_basic_req(mock_client: aiopcloud.Client, aioresp: aioresponses.aioresponses) -> None:
    payload = load_fixture_json("listfolder.json")

    aioresp.get(
        f"https://{const.TEST_BASE_URL}/listfolder?folderid=0&noshares=1",
        payload=payload,
    )

    data = await mock_client.basic_req("listfolder", folderid=0, noshares=1)
    assert data == payload

    payload = {"result": 2005, "error": "Directory does not exist."}
    aioresp.get(
        f"https://{const.TEST_BASE_URL}/listfolder?folderid=0&noshares=1",
        payload=payload,
    )

    with pytest.raises(aiopcloud.PCloudApiError) as e:
        data = await mock_client.basic_req("listfolder", folderid=0, noshares=1)
    assert e.value.args[0] == payload

    aioresp.get(
        f"https://{const.TEST_BASE_URL}/listfolder?folderid=0&noshares=1",
        status=400,
    )

    with pytest.raises(aiohttp.ClientResponseError) as e:
        data = await mock_client.basic_req("listfolder", folderid=0, noshares=1)


@pytest.mark.asyncio
async def test_upload_file(
    mock_client: aiopcloud.Client, aioresp: aioresponses.aioresponses
) -> None:
    payload = load_fixture_json("uploadfile.json")

    def callback(url: str, **kwargs: Any) -> None:  # noqa: ARG001
        assert isinstance(kwargs["data"], aiohttp.MultipartWriter)
        mp = kwargs["data"]
        assert mp._is_form_data
        assert len(mp._parts) == 1

    aioresp.post(
        f"https://{const.TEST_BASE_URL}/uploadfile?nopartial=1&path=path",
        payload=payload,
        callback=callback,
    )

    test_file = load_fixture_bytes("test.txt")

    async def async_generator_from_bytes(data: bytes) -> AsyncGenerator[bytes, Any]:
        chunks = 20
        for idx in range(0, len(data), chunks):
            yield data[idx : idx + chunks]
        return

    data = await mock_client.upload_file_iter(
        size=len(test_file),
        path="path",
        filename="test.txt",
        data=async_generator_from_bytes(test_file),
        nopartial=1,
    )
    assert data == payload


@pytest.mark.asyncio
async def test_download_file(
    mock_client: aiopcloud.Client, aioresp: aioresponses.aioresponses
) -> None:
    test_file = load_fixture_bytes("test.txt")
    getfilelink_response = {
        "result": 0,
        "path": "/test/test.txt",
        "hosts": [
            f"{const.TEST_BASE_URL}",
            "second-choice.com",
        ],
    }

    aioresp.get(
        f"https://{const.TEST_BASE_URL}/getfilelink?forcedownload=1&path=/test.txt",
        payload=getfilelink_response,
    )
    aioresp.get(
        f"https://{const.TEST_BASE_URL}/test/test.txt",
        body=test_file,
    )

    data = b""
    async for chunk in await mock_client.download_file_iter(path="/test.txt"):
        data += chunk
    assert data == test_file


@pytest.mark.asyncio
async def test_online(real_client: aiopcloud.Client) -> None:
    base_folder = "api_test"

    data = await real_client.basic_req("userinfo")
    assert data["result"] == 0

    data = await real_client.basic_req("createfolderifnotexists", folderid=0, name=base_folder)
    assert data["result"] == 0
    base_folder_id = data["metadata"]["folderid"]

    test_file = load_fixture_bytes("test.txt")

    async def async_generator_from_bytes(data: bytes) -> AsyncGenerator[bytes, Any]:
        chunks = 20
        for idx in range(0, len(data), chunks):
            yield data[idx : idx + chunks]
        return

    data = await real_client.upload_file_iter(
        size=55,
        folderid=base_folder_id,
        filename="test.txt",
        data=async_generator_from_bytes(test_file),
        nopartial=1,
    )
    assert data["result"] == 0

    data = await real_client.basic_req("listfolder", folderid=base_folder_id, noshares=1)
    assert data["result"] == 0

    data = b""
    async for chunk in await real_client.download_file_iter(path=f"/{base_folder}/test.txt"):
        data += chunk
    assert data == test_file

    data = await real_client.basic_req("deletefile", path=f"/{base_folder}/test.txt")
    assert data["result"] == 0

    data = await real_client.basic_req("deletefolder", path=f"/{base_folder}")
    assert data["result"] == 0
