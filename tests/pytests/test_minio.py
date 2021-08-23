import pytest

from urllib.parse import urlunsplit

from minio import Minio
from minio import __version__ as minio_version
from minio.api import _DEFAULT_USER_AGENT
from minio.helpers import BaseURL, check_bucket_name


def test_bucket_name():
    with pytest.raises(ValueError):
        check_bucket_name('bucketName=', False)

def test_bucket_name_invalid_characters():
    with pytest.raises(ValueError):
        check_bucket_name('$$$bcuket', False)

def test_bucket_name_length():
    with pytest.raises(ValueError):
        check_bucket_name('dd', False)

def test_bucket_name_periods():
    with pytest.raises(ValueError):
        check_bucket_name('dd..mybucket', False)

def test_bucket_name_begins_period():
    with pytest.raises(ValueError):
        check_bucket_name('.ddmybucket', False)

def test_url_build():
    url = BaseURL('http://localhost:9000', None)
    assert urlunsplit(url.build("GET", None, bucket_name='bucket-name')) == 'http://localhost:9000/bucket-name'
    assert urlunsplit(url.build("GET", None, bucket_name='bucket-name', object_name='objectName')) == 'http://localhost:9000/bucket-name/objectName'
    assert urlunsplit(url.build("GET", 'us-east-1', bucket_name='bucket-name',
                        object_name='objectName',
                        query_params={'foo': 'bar'})) == 'http://localhost:9000/bucket-name/objectName?foo=bar'
    
    assert urlunsplit(url.build("GET", 'us-east-1', bucket_name='bucket-name',
                        object_name='objectName',
                        query_params={'foo': 'bar', 'b': 'c', 'a': 'b'})) == 'http://localhost:9000/bucket-name/objectName?a=b&b=c&foo=bar'
    assert urlunsplit(
            url.build("GET", 'us-east-1', bucket_name='bucket-name', object_name='path/to/objectName/')) == 'http://localhost:9000/bucket-name/path/to/objectName/'

    # S3 urls.
    url = BaseURL('https://s3.amazonaws.com', None)
    assert urlunsplit(url.build("GET", "us-east-1")) == 'https://s3.us-east-1.amazonaws.com/'
    assert urlunsplit(url.build("GET", "eu-west-1", bucket_name='my.bucket.name')) == 'https://s3.eu-west-1.amazonaws.com/my.bucket.name'
    assert urlunsplit(url.build("GET", 'us-west-2', bucket_name='bucket-name', object_name='objectName')) == 'https://bucket-name.s3.us-west-2.amazonaws.com/objectName'
    assert urlunsplit(url.build("GET", "us-east-1", bucket_name='bucket-name', object_name='objectName', query_params={'versionId': 'uuid'})) == "https://bucket-name.s3.us-east-1.amazonaws.com/objectName?versionId=uuid"

def test_minio_requires_string(mock_client_session):
    with pytest.raises(TypeError):
        Minio(10)

def test_minio_requires_hostname(mock_client_session):
    with pytest.raises(ValueError):
        Minio('http://')


def test_default_user_agent(mock_client_session):
    client = Minio('localhost')
    assert client._user_agent == _DEFAULT_USER_AGENT

def test_set_app_info(mock_client_session):
    client = Minio('localhost')
    expected_user_agent = _DEFAULT_USER_AGENT + ' hello/' + minio_version
    client.set_app_info('hello', minio_version)
    assert client._user_agent == expected_user_agent

def test_set_app_info_requires_non_empty_name(mock_client_session):
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        client.set_app_info('', minio_version)

def test_set_app_info_requires_non_empty_version(mock_client_session):
    client = Minio('localhost:9000')
    with pytest.raises(ValueError):
        client.set_app_info('hello', '')


def test_region_none():
    region = BaseURL('http://localhost', None).region
    assert region == None

def test_region_us_west():
    region = BaseURL('https://s3-us-west-1.amazonaws.com', None).region
    assert region == None

def test_region_with_dot():
    region = BaseURL('https://s3.us-west-1.amazonaws.com', None).region
    assert region == 'us-west-1'

def test_region_with_dualstack():
    region = BaseURL(
        'https://s3.dualstack.us-west-1.amazonaws.com', None,
    ).region
    assert region == 'us-west-1'

def test_region_us_east():
    region = BaseURL('http://s3.amazonaws.com', None).region
    assert region == None

def test_invalid_value():
    with pytest.raises(ValueError):
        BaseURL(None, None)
