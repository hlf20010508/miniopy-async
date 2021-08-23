import pytest
import json

from minio import Minio
from minio.api import _DEFAULT_USER_AGENT
from minio.error import S3Error

from .conftest import MockAiohttpResponse

@pytest.mark.asyncio
async def test_get_policy_for_non_existent_bucket(mock_client_session):
    bucket_name = 'non-existent-bucket'
    error = ("<ErrorResponse>"
                "<Code>NoSuchBucket</Code>"
                "<Message>No such bucket</Message><RequestId>1234</RequestId>"
                "<Resource>/non-existent-bucket</Resource>"
                "<HostId>abcd</HostId>"
                "<BucketName>non-existent-bucket</BucketName>"
                "</ErrorResponse>")
    mock_client_session.add_mock_request(
        MockAiohttpResponse(
            'GET',
            'https://localhost:9000/' + bucket_name + '?policy=',
            {'User-Agent': _DEFAULT_USER_AGENT},
            404,
            response_headers={"Content-Type": "application/xml"},
            body=error.encode()
        )
    )
    client = Minio('localhost:9000')
    with pytest.raises(S3Error):
        await client.get_bucket_policy(bucket_name)

@pytest.mark.asyncio
async def test_get_policy_for_existent_bucket(mock_client_session):
    mock_data = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:GetBucketLocation",
                "Resource": "arn:aws:s3:::test-bucket"
            },
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:ListBucket",
                "Resource": "arn:aws:s3:::test-bucket"
            },
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::test-bucket/*"
            }
        ]
    }).encode()
    bucket_name = 'test-bucket'
    mock_client_session.add_mock_request(
        MockAiohttpResponse(
            'GET',
            'https://localhost:9000/' + bucket_name + '?policy=',
            {'User-Agent': _DEFAULT_USER_AGENT},
            200,
            body=mock_data
        )
    )
    client = Minio('localhost:9000')
    response = await client.get_bucket_policy(bucket_name)
    assert response == mock_data.decode()
