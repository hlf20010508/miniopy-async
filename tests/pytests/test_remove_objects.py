import pytest
import itertools

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT
from minio.deleteobjects import DeleteObject

from .conftest import MockAiohttpResponse

@pytest.mark.asyncio
async def test_object_is_list(mock_client_session):
    mock_client_session.add_mock_request(
        MockAiohttpResponse('POST',
                        'https://localhost:9000/hello?delete=',
                        {'User-Agent': _DEFAULT_USER_AGENT,
                        'Content-Md5': u'YcTFWle4oiLJ6sT95FwpdA=='}, 200,
                        body=b'<Delete/>')
    )
    client = Minio('localhost:9000')
    async for err in client.remove_objects(
            "hello",
            [DeleteObject("Ab"), DeleteObject("c")],
    ):
        print(err)

@pytest.mark.asyncio
async def test_object_is_tuple(mock_client_session):
    mock_client_session.add_mock_request(
        MockAiohttpResponse('POST',
                        'https://localhost:9000/hello?delete=',
                        {'User-Agent': _DEFAULT_USER_AGENT,
                        'Content-Md5': u'YcTFWle4oiLJ6sT95FwpdA=='}, 200,
                        body=b'<Delete/>')
    )
    client = Minio('localhost:9000')
    async for err in client.remove_objects(
            "hello",
            (DeleteObject("Ab"), DeleteObject("c")),
    ):
        print(err)

@pytest.mark.asyncio
async def test_object_is_iterator(mock_client_session):
    mock_client_session.add_mock_request(
        MockAiohttpResponse('POST',
                        'https://localhost:9000/hello?delete=',
                        {'User-Agent': _DEFAULT_USER_AGENT,
                        'Content-Md5': u'YcTFWle4oiLJ6sT95FwpdA=='}, 200,
                        body=b'<Delete/>')
    )
    client = Minio('localhost:9000')
    it = itertools.chain((DeleteObject("Ab"), DeleteObject("c")))
    async for err in client.remove_objects('hello', it):
        print(err)
