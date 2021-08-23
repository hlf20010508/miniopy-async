import pytest

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT
from minio.error import S3Error

from .conftest import MockAiohttpClient, MockAiohttpResponse, mock_client_session

@pytest.mark.asyncio
async def test_bucket_is_string(mock_client_session):
    client = Minio("localhost:9000")

    with pytest.raises(TypeError):
        await client.bucket_exists(1234)
    
    await client.close()


@pytest.mark.asyncio
async def test_bucket_is_not_empty_string(mock_client_session):
    client = Minio("localhost:9000")

    with pytest.raises(ValueError):
        await client.bucket_exists('  \t \n  ')

    await client.close()

@pytest.mark.asyncio
async def test_bucket_exists_invalid_name(mock_client_session):
    client = Minio("localhost:9000")

    with pytest.raises(ValueError):
        await client.bucket_exists('AB*CD')
    
    await client.close()

@pytest.mark.asyncio
async def test_bucket_exists_bad_request(mock_client_session):
    mock_client_session.add_mock_request(
            MockAiohttpResponse('HEAD', 'https://localhost:9000/hello',
            {'User-Agent': _DEFAULT_USER_AGENT}, 400
            )
        )
    
    client = Minio("localhost:9000")
    with pytest.raises(S3Error):
        await client.bucket_exists("hello")

@pytest.mark.asyncio
async def test_bucket_exists(mock_client_session):
    mock_client_session.add_mock_request(
            MockAiohttpResponse(
                         'HEAD',
                         'https://localhost:9000/hello',
                         {'User-Agent': _DEFAULT_USER_AGENT},
                         200,
                         )
        )
    client = Minio('localhost:9000')
    result = await client.bucket_exists('hello')
    assert True == result
    mock_client_session.add_mock_request(
        MockAiohttpResponse(url='https://localhost:9000/goodbye',
                        method='HEAD',
                        headers={'User-Agent': _DEFAULT_USER_AGENT},
                        status=404)
    )
    false_result = await client.bucket_exists('goodbye')
    assert False == false_result
