import pytest

from minio import Minio
from minio.commonconfig import CopySource

@pytest.mark.asyncio
async def test_valid_copy_source():
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        await client.copy_object('hello', '1', '/testbucket/object')

@pytest.mark.asyncio
async def test_valid_match_etag():
    with pytest.raises(ValueError):
        CopySource("src-bucket", "src-object", match_etag='')

@pytest.mark.asyncio
async def test_not_match_etag():
    with pytest.raises(ValueError):
        CopySource("src-bucket", "src-object", not_match_etag='')

@pytest.mark.asyncio
async def test_valid_modified_since():
    with pytest.raises(ValueError):
        CopySource("src-bucket", "src-object", modified_since='')

@pytest.mark.asyncio
async def test_valid_unmodified_since():
    with pytest.raises(ValueError):
        CopySource("src-bucket", "src-object", unmodified_since='')
