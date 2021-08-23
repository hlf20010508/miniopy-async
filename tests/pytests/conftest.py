"""
conftest.py
"""

import pytest
import json

class AsyncContentReader:
    def __init__(self, data, chunk_size=8):
      self.data = data
      self.chunk_size = chunk_size

    async def iter_chunked(self, chunk_size=1):
        for i in range(0, len(self.data), chunk_size):
            yield self.data[i:i+chunk_size]

    def __aiter__(self):
        return self

    async def __anext__(self):
        for i in range(0, len(self.data), self.chunk_size):
            yield self.data[i:i+self.chunk_size]
            
class MockAiohttpResponse:
    def __init__(self, method="GET", url="", headers={}, status=200, body=None, response_headers={}):
        self.status = status
        self.request_headers = {
            key.lower(): value for key, value in headers.items()
        }
        self.headers = {
            key.lower(): value for key, value in (
                response_headers or {}).items()
        }
        self.body = body
        self.url = url
        self.method = method

    def mock_verify(self, method, url, headers):
        assert self.method == method
        assert self.url == url

        headers = {
            key.lower(): value for key, value in headers.items()
        }

        for k in self.request_headers:
            assert k in headers
            assert self.request_headers[k] == headers[k]

    async def json(self):
        return json.loads(self.body)

    async def content(self):
        return AsyncContentReader(self.body)

    async def text(self):
       if self.body:
           return self.body.decode()

class MockAiohttpClient:
    def __init__(self):
        self.requests = []

    def add_mock_request(self, request):
        self.requests.append(request)

    async def request(self, method, url, *, headers=None, data=None, json=None):
        return_request = self.requests[0]
        return_request.mock_verify(method, url, headers)
        return self.requests.pop(0)
    
    async def close(self):
        pass

class CredListResponse(object):
    status = 200
    data = b"test-s3-full-access-for-minio-ec2"

    async def text(self):
        return self.data.decode()


class CredsResponse(object):
    status = 200
    data = json.dumps({
        "Code": "Success",
        "Type": "AWS-HMAC",
        "AccessKeyId": "accessKey",
        "SecretAccessKey": "secret",
        "Token": "token",
        "Expiration": "2014-12-16T01:51:37Z",
        "LastUpdated": "2009-11-23T0:00:00Z"
    })

    async def text(self):
        return self.data.encode()
    
    async def json(self):
        return json.loads(self.data)

async def response_return(response):
    return response

@pytest.fixture
def mock_client_session(mocker):
    mock_connection = mocker.patch("aiohttp.ClientSession")
    mock_server = MockAiohttpClient()
    mock_connection.return_value = mock_server
    return mock_server

@pytest.fixture
def cred_client_response(mocker):
    mock_connection = mocker.patch("aiohttp.ClientSession.request")
    mock_server = MockAiohttpClient()
    mock_connection.return_value = mock_server
    mock_connection.side_effect = [response_return(CredListResponse()), response_return(CredsResponse())]
    return mock_server