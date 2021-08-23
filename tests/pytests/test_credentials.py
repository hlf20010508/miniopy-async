import json
import os
import pytest
from datetime import datetime, timedelta

import mock

from minio.credentials.credentials import Credentials
from minio.credentials.providers import (AWSConfigProvider, ChainedProvider,
                                         EnvAWSProvider, EnvMinioProvider,
                                         IamAwsProvider,
                                         MinioClientConfigProvider,
                                         StaticProvider)

CONFIG_JSON_SAMPLE = "./tests/pytests/config.json.sample"
CREDENTIALS_SAMPLE = "./tests/pytests/credentials.sample"
CREDENTIALS_EMPTY = "./tests/pytests/credentials.empty"

@pytest.mark.asyncio
async def test_credentials_get():
    provider = MinioClientConfigProvider(
        filename=CONFIG_JSON_SAMPLE,
        alias="play",
    )
    creds = await provider.retrieve()
    assert creds.access_key == "Q3AM3UQ867SPQQA43P2F"
    assert creds.secret_key == "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
    assert creds.session_token == None

@pytest.mark.asyncio
async def test_iam(cred_client_response):
    provider = IamAwsProvider()
    creds = await provider.retrieve()
    assert creds.access_key == "accessKey"
    assert creds.secret_key == "secret"
    assert creds.session_token == "token"
    assert creds._expiration == datetime(2014, 12, 16, 1, 51, 37)

@pytest.mark.asyncio
async def test_chain_retrieve():
    # clear environment
    os.environ.clear()
    # prepare env for env_aws provider
    os.environ["AWS_ACCESS_KEY_ID"] = "access_aws"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "secret_aws"
    os.environ["AWS_SESSION_TOKEN"] = "token_aws"
    # prepare env for env_minio
    os.environ["MINIO_ACCESS_KEY"] = "access_minio"
    os.environ["MINIO_SECRET_KEY"] = "secret_minio"
    # create chain provider with env_aws and env_minio providers

    provider = ChainedProvider(
        [
            EnvAWSProvider(), EnvMinioProvider(),
        ]
    )
    # retireve provider (env_aws) has priority
    creds = await provider.retrieve()
    # assert provider credentials
    assert creds.access_key == "access_aws"
    assert creds.secret_key == "secret_aws"
    assert creds.session_token == "token_aws"

@pytest.mark.asyncio
async def test_env_aws_retrieve():
    os.environ.clear()
    os.environ["AWS_ACCESS_KEY_ID"] = "access"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "secret"
    os.environ["AWS_SESSION_TOKEN"] = "token"
    provider = EnvAWSProvider()
    creds = await provider.retrieve()
    assert creds.access_key == "access"
    assert creds.secret_key == "secret"
    assert creds.session_token == "token"

@pytest.mark.asyncio
async def test_env_aws_retrieve_no_token():
    os.environ.clear()
    os.environ["AWS_ACCESS_KEY_ID"] = "access"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "secret"
    provider = EnvAWSProvider()
    creds = await provider.retrieve()
    assert creds.access_key == "access"
    assert creds.secret_key == "secret"
    assert creds.session_token == None

@pytest.mark.asyncio
async def test_env_minio_retrieve():
    os.environ.clear()
    os.environ['MINIO_ACCESS_KEY'] = "access"
    os.environ["MINIO_SECRET_KEY"] = "secret"
    provider = EnvMinioProvider()
    creds = await provider.retrieve()
    assert creds.access_key == "access"
    assert creds.secret_key == "secret"
    assert creds.session_token == None

@pytest.mark.asyncio
async def test_file_aws():
    os.environ.clear()
    provider = AWSConfigProvider(CREDENTIALS_SAMPLE)
    creds = await provider.retrieve()
    assert creds.access_key == "accessKey"
    assert creds.secret_key == "secret"
    assert creds.session_token == "token"

@pytest.mark.asyncio
async def test_file_aws_from_env():
    os.environ.clear()
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = (
        CREDENTIALS_SAMPLE
    )
    provider = AWSConfigProvider()
    creds = await provider.retrieve()
    assert creds.access_key == "accessKey"
    assert creds.secret_key == "secret"
    assert creds.session_token == "token"

@pytest.mark.asyncio
async def test_file_aws_env_profile():
    os.environ.clear()
    os.environ["AWS_PROFILE"] = "no_token"
    provider = AWSConfigProvider(CREDENTIALS_SAMPLE)
    creds = await provider.retrieve()
    assert creds.access_key == "accessKey"
    assert creds.secret_key == "secret"
    assert creds.session_token == None

@pytest.mark.asyncio
async def test_file_aws_arg_profile():
    os.environ.clear()
    provider = AWSConfigProvider(
        CREDENTIALS_SAMPLE,
        "no_token",
    )
    creds = await provider.retrieve()
    assert creds.access_key == "accessKey"
    assert creds.secret_key == "secret"
    assert creds.session_token == None

@pytest.mark.asyncio
async def test_file_aws_no_creds():
    os.environ.clear()
    provider = AWSConfigProvider(
        CREDENTIALS_EMPTY,
        "no_token",
    )
    try:
        await provider.retrieve()
    except ValueError:
        pass

@pytest.mark.asyncio
async def test_file_minio():
    os.environ.clear()
    provider = MinioClientConfigProvider(filename=CONFIG_JSON_SAMPLE)
    creds = await provider.retrieve()
    assert creds.access_key == "accessKey"
    assert creds.secret_key == "secret"
    assert creds.session_token == None

@pytest.mark.asyncio
async def test_file_minio_env_alias():
    os.environ.clear()
    os.environ["MINIO_ALIAS"] = "play"
    provider = MinioClientConfigProvider(filename=CONFIG_JSON_SAMPLE)
    creds = await provider.retrieve()
    assert creds.access_key == "Q3AM3UQ867SPQQA43P2F"
    assert creds.secret_key == "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
    assert creds.session_token == None

@pytest.mark.asyncio
async def test_file_minio_arg_alias():
    os.environ.clear()
    provider = MinioClientConfigProvider(
        filename=CONFIG_JSON_SAMPLE,
        alias="play",
    )
    creds = await provider.retrieve()
    assert creds.access_key == "Q3AM3UQ867SPQQA43P2F"
    assert creds.secret_key == "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
    assert creds.session_token == None

@pytest.mark.asyncio
async def test_static_credentials():
    provider = StaticProvider("UXHW", "SECRET")
    creds = await provider.retrieve()
    assert creds.access_key == "UXHW"
    assert creds.secret_key == "SECRET"
    assert creds.session_token == None