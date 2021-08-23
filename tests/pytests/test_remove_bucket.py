import pytest

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT

from .conftest import MockAiohttpResponse, MockAiohttpClient

@pytest.mark.asyncio
async def test_bucket_is_string():
    client = Minio('localhost:9000')
    with pytest.raises(TypeError):
        await client.remove_bucket(1234)

@pytest.mark.asyncio
async def test_bucket_is_not_empty_string():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.remove_bucket('  \t \n  ')

@pytest.mark.asyncio
async def test_remove_bucket_invalid_name():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.remove_bucket('AB*CD')

@pytest.mark.asyncio
async def test_remove_bucket_works(mock_client_session):
    mock_client_session.add_mock_request(
        MockAiohttpResponse('DELETE',
                        'https://localhost:9000/hello',
                        {'User-Agent': _DEFAULT_USER_AGENT}, 204)
    )
    client = Minio('localhost:9000')
    await client.remove_bucket('hello')
