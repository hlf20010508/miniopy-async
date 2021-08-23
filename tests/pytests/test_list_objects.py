import pytest

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT
from minio.error import S3Error

from .conftest import MockAiohttpResponse, MockAiohttpClient

@pytest.mark.asyncio
async def test_empty_list_objects_works(mock_client_session):
    mock_data = '''<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Name>bucket</Name>
<Prefix></Prefix>
<KeyCount>0</KeyCount>
<MaxKeys>1000</MaxKeys>
<Delimiter></Delimiter>
<IsTruncated>false</IsTruncated>
</ListBucketResult>'''
    mock_client_session.add_mock_request(
        MockAiohttpResponse(
            "GET",
            "https://localhost:9000/bucket?delimiter=&encoding-type=url"
            "&list-type=2&max-keys=1000&prefix=",
            {"User-Agent": _DEFAULT_USER_AGENT},
            200,
            body=mock_data.encode(),
        ),
    )
    client = Minio('localhost:9000')
    object_iter = await client.list_objects('bucket', recursive=True)
    objects = []
    for obj in object_iter:
        objects.append(obj)
    assert 0 == len(objects)

@pytest.mark.asyncio
async def test_list_objects_works(mock_client_session):
    mock_data = '''<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Name>bucket</Name>
<Prefix></Prefix>
<KeyCount>2</KeyCount>
<MaxKeys>1000</MaxKeys>
<IsTruncated>false</IsTruncated>
<Contents>
<Key>6/f/9/6f9898076bb08572403f95dbb86c5b9c85e1e1b3</Key>
<LastModified>2016-11-27T07:55:53.000Z</LastModified>
<ETag>&quot;5d5512301b6b6e247b8aec334b2cf7ea&quot;</ETag>
<Size>493</Size>
<StorageClass>REDUCED_REDUNDANCY</StorageClass>
</Contents>
<Contents>
<Key>b/d/7/bd7f6410cced55228902d881c2954ebc826d7464</Key>
<LastModified>2016-11-27T07:10:27.000Z</LastModified>
<ETag>&quot;f00483d523ffc8b7f2883ae896769d85&quot;</ETag>
<Size>493</Size>
<StorageClass>REDUCED_REDUNDANCY</StorageClass>
</Contents>
</ListBucketResult>'''
    mock_client_session.add_mock_request(
        MockAiohttpResponse(
            "GET",
            "https://localhost:9000/bucket?delimiter=%2F&encoding-type=url"
            "&list-type=2&max-keys=1000&prefix=",
            {"User-Agent": _DEFAULT_USER_AGENT},
            200,
            body=mock_data.encode(),
        ),
    )
    client = Minio('localhost:9000')
    objects_iter = await client.list_objects('bucket')
    objects = []
    for obj in objects_iter:
        objects.append(obj)

    assert 2 == len(objects)
