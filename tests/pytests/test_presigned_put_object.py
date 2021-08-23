import pytest

from datetime import timedelta

from minio import Minio

@pytest.mark.asyncio
async def test_object_is_string():
    client = Minio('localhost:9000')
    with pytest.raises(TypeError):
        await client.presigned_put_object('hello', 1234)

@pytest.mark.asyncio
async def test_object_is_not_empty_string():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.presigned_put_object('hello', ' \t \n ')

@pytest.mark.asyncio
async def test_expiry_limit():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.presigned_put_object('hello', 'key', expires=timedelta(days=8))
