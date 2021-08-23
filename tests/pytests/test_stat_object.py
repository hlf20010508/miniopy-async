import pytest

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT

from .conftest import MockAiohttpResponse

@pytest.mark.asyncio
async def test_object_is_string():
    client = Minio('localhost:9000')
    with pytest.raises(TypeError):
        await client.stat_object('hello', 1234)

@pytest.mark.asyncio
async def test_object_is_not_empty_string():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.stat_object('hello', '  \t \n  ')

@pytest.mark.asyncio
async def test_stat_object_invalid_name():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.stat_object('AB#CD', 'world')

@pytest.mark.asyncio
async def test_stat_object_works(mock_client_session):
    mock_headers = {
        'content-type': 'application/octet-stream',
        'last-modified': 'Fri, 26 Jun 2015 19:05:37 GMT',
        'content-length': 11,
        'etag': '5eb63bbbe01eeed093cb22bb8f5acdc3'
    }
    mock_client_session.add_mock_request(
        MockAiohttpResponse('HEAD',
                        'https://localhost:9000/hello/world',
                        {'User-Agent': _DEFAULT_USER_AGENT}, 200,
                        response_headers=mock_headers)
    )
    client = Minio('localhost:9000')
    await client.stat_object('hello', 'world')
