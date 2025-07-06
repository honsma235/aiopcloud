# ruff: noqa: ANN201
import os

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses
from dotenv import load_dotenv

from aiopcloud import AbstractAuth, Client
from tests import const

load_dotenv()


@pytest_asyncio.fixture
async def mock_client():
    class MockAuth(AbstractAuth):
        async def async_get_access_token(self) -> str:
            return "12345"

    async with aiohttp.ClientSession() as session:
        auth = MockAuth(session, const.TEST_BASE_URL)
        client = Client(auth)
        yield client


@pytest_asyncio.fixture
async def real_client():
    # get token
    # https://my.pcloud.com/oauth2/authorize?client_id=xxx&response_type=code
    # https://[e]api.pcloud.com/oauth2_token?client_id=xxx&client_secret=yyy&code=xxx

    token = os.environ.get("EAPI_PCLOUD_COM_TEST_TOKEN")
    if token is None:
        pytest.skip(
            "set a environment variable (or .env) 'EAPI_PCLOUD_COM_TEST_TOKEN' with a valid token"
        )
    hostname = "eapi.pcloud.com"

    class MockAuth(AbstractAuth):
        async def async_get_access_token(self) -> str:
            return token

    async with aiohttp.ClientSession() as session:
        auth = MockAuth(session, hostname)
        client = Client(auth)
        yield client


@pytest_asyncio.fixture
def aioresp():
    with aioresponses() as m:
        yield m
