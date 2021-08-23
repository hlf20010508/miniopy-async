import pytest

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT

from .conftest import MockAiohttpClient, MockAiohttpResponse

@pytest.mark.asyncio
async def test_object_is_string():
    client = Minio('localhost:9000')
    with pytest.raises(TypeError):
        await client.put_object('hello', 1234, 1, iter([1, 2, 3]))

@pytest.mark.asyncio
async def test_object_is_not_empty_string():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.put_object('hello', ' \t \n ', 1, iter([1, 2, 3]))

@pytest.mark.asyncio
async def test_length_is_string():
    client = Minio('localhost:9000')
    with pytest.raises(TypeError):
        await client.put_object('hello', 1234, '1', iter([1, 2, 3]))

@pytest.mark.asyncio
async def test_length_is_not_empty_string():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.put_object('hello', ' \t \n ', -1, iter([1, 2, 3]))
