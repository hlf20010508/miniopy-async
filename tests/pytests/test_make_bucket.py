import pytest

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT
from minio.error import S3Error

from .helpers import generate_error
from .conftest import MockAiohttpResponse, MockAiohttpClient

@pytest.mark.asyncio
async def test_bucket_is_string():
    client = Minio('localhost:9000')
    with pytest.raises(TypeError):
        await client.make_bucket(1234)

@pytest.mark.asyncio
async def test_bucket_is_not_empty_string():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.make_bucket('  \t \n  ')

@pytest.mark.asyncio
async def test_make_bucket_works(mock_client_session):
    mock_client_session.add_mock_request(
        MockAiohttpResponse('PUT',
                        'https://localhost:9000/hello',
                        {'User-Agent': _DEFAULT_USER_AGENT},
                        200)
    )
    Minio('localhost:9000')


@pytest.mark.asyncio
async def test_make_bucket_throws_fail(mock_client_session):
    error_xml = generate_error('code', 'message', 'request_id',
                                'host_id', 'resource', 'bucket',
                                'object')
    mock_client_session.add_mock_request(
        MockAiohttpResponse('PUT',
                        'https://localhost:9000/hello',
                        {'User-Agent': _DEFAULT_USER_AGENT},
                        409,
                        response_headers={"Content-Type": "application/xml"},
                        body=error_xml.encode())
    )
    client = Minio('localhost:9000')
    with pytest.raises(S3Error):
        await client.make_bucket('hello')
