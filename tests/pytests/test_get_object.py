import pytest

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT
from minio.error import S3Error


from .conftest import MockAiohttpResponse, MockAiohttpClient

from .helpers import generate_error

@pytest.mark.asyncio
async def test_object_is_string():
    client = Minio('localhost:9000')
    with pytest.raises(TypeError):
        await client.get_object('hello', 1234)

@pytest.mark.asyncio
async def test_object_is_not_empty_string():
    client = Minio('localhost:9000')

    with pytest.raises(ValueError):
        await client.get_object('hello', ' \t \n ')

@pytest.mark.asyncio
async def test_get_object_throws_fail(mock_client_session):
    error_xml = generate_error('code', 'message', 'request_id',
                                   'host_id', 'resource', 'bucket',
                                   'object')
    
    mock_client_session.add_mock_request(
        MockAiohttpResponse(method='GET',
                        url='https://localhost:9000/hello/key',
                        headers={'User-Agent': _DEFAULT_USER_AGENT},
                        status=404,
                        response_headers={"Content-Type": "application/xml"},
                        body=error_xml.encode())
    )
    client = Minio('localhost:9000')
    with pytest.raises(S3Error):
        await client.get_object('hello', 'key')


