import pytest

from datetime import datetime, timezone

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT

from .conftest import MockAiohttpClient, MockAiohttpResponse

@pytest.mark.asyncio
async def test_empty_list_buckets_works(mock_client_session):
    mock_data = ('<ListAllMyBucketsResult '
                     'xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                     '<Buckets></Buckets><Owner><ID>minio</ID><DisplayName>'
                     'minio</DisplayName></Owner></ListAllMyBucketsResult>')
    
    mock_client_session.add_mock_request(
            MockAiohttpResponse(method='GET', url='https://localhost:9000/',
                         headers={'User-Agent': _DEFAULT_USER_AGENT},
                         status=200, body=mock_data.encode())
        )
    client = Minio('localhost:9000')
    buckets = await client.list_buckets()
    count = 0
    for bucket in buckets:
        count += 1
    assert 0 == count

@pytest.mark.asyncio
async def test_list_buckets_works(mock_client_session):
    mock_data = ('<ListAllMyBucketsResult '
                     'xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                     '<Buckets><Bucket><Name>hello</Name>'
                     '<CreationDate>2015-06-22T23:07:43.240Z</CreationDate>'
                     '</Bucket><Bucket><Name>world</Name>'
                     '<CreationDate>2015-06-22T23:07:56.766Z</CreationDate>'
                     '</Bucket></Buckets><Owner><ID>minio</ID>'
                     '<DisplayName>minio</DisplayName></Owner>'
                     '</ListAllMyBucketsResult>')
    mock_client_session.add_mock_request(
            MockAiohttpResponse('GET', 'https://localhost:9000/',
                         {'User-Agent': _DEFAULT_USER_AGENT},
                         200, body=mock_data.encode())
        )
    client = Minio('localhost:9000')
    buckets = await client.list_buckets()
    buckets_list = []
    count = 0
    for bucket in buckets:
        count += 1
        buckets_list.append(bucket)
    assert 2 == count
    assert 'hello' == buckets_list[0].name
    assert datetime(2015, 6, 22, 23, 7, 43, 240000, timezone.utc) ==  buckets_list[0].creation_date
    assert 'world' == buckets_list[1].name
    assert datetime(2015, 6, 22, 23, 7, 56, 766000, timezone.utc) == buckets_list[1].creation_date

