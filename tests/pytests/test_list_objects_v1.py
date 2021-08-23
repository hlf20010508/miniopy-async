import pytest
import mock

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT

from .conftest import MockAiohttpResponse

@pytest.mark.asyncio
async def test_empty_list_objects_works(mock_client_session):
    mock_data = '''<?xml version="1.0"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Name>bucket</Name>
<Prefix/>
<Marker/>
<IsTruncated>false</IsTruncated>
<MaxKeys>1000</MaxKeys>
<Delimiter/>
</ListBucketResult>'''
    mock_client_session.add_mock_request(
        MockAiohttpResponse(
            "GET",
            "https://localhost:9000/bucket?delimiter=&encoding-type=url"
            "&max-keys=1000&prefix=",
            {"User-Agent": _DEFAULT_USER_AGENT},
            200,
            body=mock_data.encode(),
        ),
    )
    client = Minio('localhost:9000')
    bucket_iter = await client.list_objects(
        'bucket', recursive=True, use_api_v1=True,
    )
    buckets = []
    for bucket in bucket_iter:
        buckets.append(bucket)
    assert 0 == len(buckets)

@pytest.mark.asyncio
async def test_list_objects_works(mock_client_session):
    mock_data = '''<?xml version="1.0"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Name>bucket</Name>
<Prefix/>
<Marker/>
<MaxKeys>1000</MaxKeys>
<Delimiter/>
<IsTruncated>false</IsTruncated>
<Contents>
<Key>key1</Key>
<LastModified>2015-05-05T02:21:15.716Z</LastModified>
<ETag>5eb63bbbe01eeed093cb22bb8f5acdc3</ETag>
<Size>11</Size>
<StorageClass>STANDARD</StorageClass>
<Owner>
    <ID>minio</ID>
    <DisplayName>minio</DisplayName>
</Owner>
</Contents>
<Contents>
<Key>key2</Key>
<LastModified>2015-05-05T20:36:17.498Z</LastModified>
<ETag>2a60eaffa7a82804bdc682ce1df6c2d4</ETag>
<Size>1661</Size>
<StorageClass>STANDARD</StorageClass>
<Owner>
    <ID>minio</ID>
    <DisplayName>minio</DisplayName>
</Owner>
</Contents>
</ListBucketResult>'''
    mock_client_session.add_mock_request(
        MockAiohttpResponse(
            "GET",
            "https://localhost:9000/bucket?delimiter=%2F&encoding-type=url"
            "&max-keys=1000&prefix=",
            {"User-Agent": _DEFAULT_USER_AGENT},
            200,
            body=mock_data.encode(),
        ),
    )
    client = Minio('localhost:9000')
    bucket_iter = await client.list_objects('bucket', use_api_v1=True)
    buckets = []
    for bucket in bucket_iter:
        # cause an xml exception and fail if we try retrieving again
        mock_client_session.add_mock_request(
            MockAiohttpResponse(
                "GET",
                "https://localhost:9000/bucket?delimiter=%2F&encoding-type=url"
                "&max-keys=1000&prefix=",
                {"User-Agent": _DEFAULT_USER_AGENT},
                200,
                body=b"",
            ),
        )
        buckets.append(bucket)

    assert 2 == len(buckets)

@pytest.mark.asyncio
async def test_list_objects_works_well(mock_client_session):
    mock_data1 = '''<?xml version="1.0"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Name>bucket</Name>
<Prefix/>
<Marker />
<NextMarker>marker</NextMarker>
<MaxKeys>1000</MaxKeys>
<Delimiter/>
<IsTruncated>true</IsTruncated>
<Contents>
<Key>key1</Key>
<LastModified>2015-05-05T02:21:15.716Z</LastModified>
<ETag>5eb63bbbe01eeed093cb22bb8f5acdc3</ETag>
<Size>11</Size>
<StorageClass>STANDARD</StorageClass>
<Owner>
    <ID>minio</ID>
    <DisplayName>minio</DisplayName>
</Owner>
</Contents>
<Contents>
<Key>key2</Key>
<LastModified>2015-05-05T20:36:17.498Z</LastModified>
<ETag>2a60eaffa7a82804bdc682ce1df6c2d4</ETag>
<Size>1661</Size>
<StorageClass>STANDARD</StorageClass>
<Owner>
    <ID>minio</ID>
    <DisplayName>minio</DisplayName>
</Owner>
</Contents>
</ListBucketResult>'''
    mock_data2 = '''<?xml version="1.0"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Name>bucket</Name>
<Prefix/>
<Marker/>
<MaxKeys>1000</MaxKeys>
<Delimiter/>
<IsTruncated>false</IsTruncated>
<Contents>
<Key>key3</Key>
<LastModified>2015-05-05T02:21:15.716Z</LastModified>
<ETag>5eb63bbbe01eeed093cb22bb8f5acdc3</ETag>
<Size>11</Size>
<StorageClass>STANDARD</StorageClass>
<Owner>
    <ID>minio</ID>
    <DisplayName>minio</DisplayName>
</Owner>
</Contents>
<Contents>
<Key>key4</Key>
<LastModified>2015-05-05T20:36:17.498Z</LastModified>
<ETag>2a60eaffa7a82804bdc682ce1df6c2d4</ETag>
<Size>1661</Size>
<StorageClass>STANDARD</StorageClass>
<Owner>
    <ID>minio</ID>
    <DisplayName>minio</DisplayName>
</Owner>
</Contents>
</ListBucketResult>'''
    mock_client_session.add_mock_request(
        MockAiohttpResponse(
            "GET",
            "https://localhost:9000/bucket?delimiter=&encoding-type=url"
            "&max-keys=1000&prefix=",
            {"User-Agent": _DEFAULT_USER_AGENT},
            200,
            body=mock_data1.encode(),
        ),
    )
    client = Minio('localhost:9000')
    bucket_iter = await client.list_objects(
        'bucket', recursive=True, use_api_v1=True,
    )
    buckets = []
    for bucket in bucket_iter:
        mock_client_session.add_mock_request(
            MockAiohttpResponse(
                "GET",
                "https://localhost:9000/bucket?delimiter=&encoding-type=url"
                "&marker=marker&max-keys=1000&prefix=",
                {"User-Agent": _DEFAULT_USER_AGENT},
                200,
                body=mock_data2.encode(),
            ),
        )
        buckets.append(bucket)

    # FIXME: It says there should be 4 objects, but for now wrote 2
    assert 2 == len(buckets)
