import pytest
import mock

from datetime import timedelta

from minio import Minio

@pytest.mark.asyncio
async def test_object_is_string():
    client = Minio('localhost:9000')
    with pytest.raises(TypeError):
        await client.presigned_get_object('hello', 1234)

@pytest.mark.asyncio
async def test_object_is_not_empty_string():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.presigned_get_object('hello', ' \t \n ')

@pytest.mark.asyncio
async def test_expiry_limit():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.presigned_get_object('hello', 'key', expires=timedelta(days=8))

@pytest.mark.asyncio
async def test_can_include_response_headers():
    client = Minio('localhost:9000', 'my_access_key', 'my_secret_key',
                    secure=True)
    client._get_region = mock.AsyncMock(return_value='us-east-1')
    r = await client.presigned_get_object(
        'mybucket', 'myfile.pdf',
        response_headers={
            'Response-Content-Type': 'application/pdf',
            'Response-Content-Disposition': 'inline;  filename="test.pdf"'
        })
    assert 'inline' in r
    assert 'test.pdf' in r
    assert 'application%2Fpdf' in r

