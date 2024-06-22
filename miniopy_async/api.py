# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
# (C) 2015, 2016, 2017 MinIO, Inc.
# (C) 2022 Huseyn Mashadiyev <mashadiyev.huseyn@gmail.com>
# (C) 2022 L-ING <hlf01@icloud.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# NOTICE: This file has been changed and differs from the original
# Author: L-ING
# Date: 2022-07-11

# pylint: disable=too-many-lines,disable=too-many-branches,too-many-statements
# pylint: disable=too-many-arguments

"""
Simple Storage Service (aka S3) client to perform bucket and object operations.
"""

from __future__ import absolute_import

import asyncio
import itertools
import os
import platform
from random import random
from io import BytesIO
import tarfile

# import weakref
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlunsplit
from xml.etree import ElementTree as ET

import aiofile
import aiohttp

from . import __title__, __version__, time
from .commonconfig import COPY, ComposeSource, CopySource, REPLACE, Tags, SnowballObject
from .credentials import StaticProvider
from .datatypes import (
    AsyncEventIterable,
    CompleteMultipartUploadResult,
    ListAllMyBucketsResult,
    ListMultipartUploadsResult,
    ListPartsResult,
    Object,
    Part,
    PostPolicy,
    parse_copy_object,
    parse_list_objects,
    ListObjects,
)
from .deleteobjects import DeleteError, DeleteRequest, DeleteResult
from .error import InvalidResponseError, S3Error, ServerError
from .helpers import (
    BaseURL,
    MAX_MULTIPART_COUNT,
    MAX_MULTIPART_OBJECT_SIZE,
    MAX_PART_SIZE,
    MIN_PART_SIZE,
    ObjectWriteResult,
    check_bucket_name,
    check_non_empty_string,
    check_sse,
    check_ssec,
    genheaders,
    get_part_info,
    is_valid_policy_type,
    makedirs,
    md5sum_hash,
    read_part_data,
    sha256_hash,
)
from .legalhold import LegalHold
from .lifecycleconfig import LifecycleConfig
from .notificationconfig import NotificationConfig
from .objectlockconfig import ObjectLockConfig
from .progress import Progress
from .replicationconfig import ReplicationConfig
from .retention import Retention
from .select import SelectObjectReader, SelectRequest
from .signer import presign_v4, sign_v4_s3
from .sse import SseCustomerKey
from .sseconfig import SSEConfig
from .tagging import Tagging
from .versioningconfig import VersioningConfig
from .xml import Element, SubElement, findtext, getbytes, marshal, unmarshal

_DEFAULT_USER_AGENT = "MinIO ({os}; {arch}) {lib}/{ver}".format(
    os=platform.system(),
    arch=platform.machine(),
    lib=__title__,
    ver=__version__,
)


class Minio:  # pylint: disable=too-many-public-methods
    """
    Simple Storage Service (aka S3) client to perform bucket and object
    operations.

    :param endpoint: Hostname of a S3 service.
    :param access_key: Access key (aka user ID) of your account in S3 service.
    :param secret_key: Secret Key (aka password) of your account in S3 service.
    :param session_token: Session token of your account in S3 service.
    :param secure: Flag to indicate to use secure (TLS) connection to S3
        service or not.
    :param region: Region name of buckets in S3 service.
    :param http_client: Customized HTTP client.
    :param credentials: Credentials provider of your account in S3 service.
    :param cert_check: Flag to indicate to verify SSL certificate or not.
    :return: :class:`Minio <Minio>` object

    Example::
        # Create client with anonymous access.
        client = Minio("play.min.io")

        # Create client with access and secret key.
        client = Minio("s3.amazonaws.com", "ACCESS-KEY", "SECRET-KEY")

        # Create client with access key and secret key with specific region.
        client = Minio(
            "play.minio.io:9000",
            access_key="Q3AM3UQ867SPQQA43P2F",
            secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
            region="my-region",
        )

    **NOTE on concurrent usage:** `Minio` object is thread safe when using
    the Python `threading` library. Specifically, it is **NOT** safe to share
    it between multiple processes, for example when using
    `multiprocessing.Pool`. The solution is simply to create a new `Minio`
    object in each process, and not share it between processes.

    """

    # pylint: disable=too-many-function-args
    def __init__(
        self,
        endpoint,
        access_key=None,
        secret_key=None,
        session_token=None,
        secure=True,
        region=None,
        credentials=None,
        cert_check=True,
    ):
        self._region_map = dict()
        self._base_url = BaseURL(
            ("https://" if secure else "http://") + endpoint,
            region,
        )
        self._user_agent = _DEFAULT_USER_AGENT
        if access_key:
            credentials = StaticProvider(access_key, secret_key, session_token)
        self._provider = credentials
        self._ssl = None if cert_check else False

    def _handle_redirect_response(self, method, bucket_name, response, retry=False):
        """
        Handle redirect response indicates whether retry HEAD request
        on failure.
        """
        code, message = {
            301: ("PermanentRedirect", "Moved Permanently"),
            307: ("Redirect", "Temporary redirect"),
            400: ("BadRequest", "Bad request"),
        }.get(response.status, (None, None))
        region = response.headers.get("x-amz-bucket-region")
        if message and region:
            message += "; use region " + region

        if (
            retry
            and region
            and method == "HEAD"
            and bucket_name
            and self._region_map.get(bucket_name)
        ):
            code, message = ("RetryHead", None)

        return code, message

    async def _build_headers(self, host, headers, body, credentials):
        """Build headers with given parameters."""
        headers = headers or {}
        md5sum_added = headers.get("Content-MD5")
        headers["Host"] = host
        headers["User-Agent"] = self._user_agent
        sha256 = None
        md5sum = None

        if body:
            headers["Content-Length"] = str(len(body))
        if credentials:
            if self._base_url.is_https:
                sha256 = "UNSIGNED-PAYLOAD"
                md5sum = None if md5sum_added else md5sum_hash(body)
            else:
                _current_event_loop = asyncio.get_event_loop()
                _thread_pool_executor = ThreadPoolExecutor(max_workers=16)
                sha256 = await _current_event_loop.run_in_executor(
                    _thread_pool_executor, sha256_hash, body
                )
        else:
            md5sum = None if md5sum_added else md5sum_hash(body)
        if md5sum:
            headers["Content-MD5"] = md5sum
        if sha256:
            headers["x-amz-content-sha256"] = sha256
        if credentials and credentials.session_token:
            headers["X-Amz-Security-Token"] = credentials.session_token
        date = time.utcnow()
        headers["x-amz-date"] = time.to_amz_date(date)
        return headers, date

    async def _url_open(  # pylint: disable=too-many-branches
        self,
        method,
        region,
        bucket_name=None,
        object_name=None,
        body=None,
        headers=None,
        query_params=None,
        session=None,
    ):
        """Execute HTTP request."""
        credentials = self._provider.retrieve() if self._provider else None
        url = self._base_url.build(
            method,
            region,
            bucket_name=bucket_name,
            object_name=object_name,
            query_params=query_params,
        )
        headers, date = await self._build_headers(
            url.netloc, headers, body, credentials
        )
        if credentials:
            headers = sign_v4_s3(
                method,
                url,
                region,
                headers,
                credentials,
                headers.get("x-amz-content-sha256"),
                date,
            )

        if session is None:
            session = aiohttp.ClientSession()

        response = await session.request(
            method, urlunsplit(url), data=body, headers=headers, ssl=self._ssl
        )

        if response.status in [200, 204, 206]:
            return response

        response_data = await response.content.read()
        content_types = response.headers.get("content-type", "").split(";")
        if method != "HEAD" and "application/xml" not in content_types:
            raise InvalidResponseError(
                response.status,
                response.headers.get("content-type"),
                response_data if response_data else None,
            )

        if not response_data and method != "HEAD":
            raise InvalidResponseError(
                response.status,
                response.headers.get("content-type"),
                None,
            )

        response_error = (
            S3Error.fromxml(response, response_data) if response_data else None
        )

        error_map = {
            301: lambda: self._handle_redirect_response(
                method,
                bucket_name,
                response,
                True,
            ),
            307: lambda: self._handle_redirect_response(
                method,
                bucket_name,
                response,
                True,
            ),
            400: lambda: self._handle_redirect_response(
                method,
                bucket_name,
                response,
                True,
            ),
            403: lambda: ("AccessDenied", "Access denied"),
            404: lambda: (
                ("NoSuchKey", "Object does not exist")
                if object_name
                else (
                    ("NoSuchBucket", "Bucket does not exist")
                    if bucket_name
                    else ("ResourceNotFound", "Request resource not found")
                )
            ),
            405: lambda: (
                "MethodNotAllowed",
                "The specified method is not allowed against this resource",
            ),
            409: lambda: (
                (
                    ("NoSuchBucket", "Bucket does not exist")
                    if bucket_name
                    else ("ResourceConflict", "Request resource conflicts")
                ),
            ),
            501: lambda: (
                "MethodNotAllowed",
                "The specified method is not allowed against this resource",
            ),
        }

        if not response_error:
            func = error_map.get(response.status)
            code, message = func() if func else (None, None)
            if not code:
                raise ServerError(
                    f"server failed with HTTP status code {response.status}",
                    response.status,
                )
            response_error = S3Error(
                code,
                message,
                url.path,
                response.headers.get("x-amz-request-id"),
                response.headers.get("x-amz-id-2"),
                response,
                bucket_name=bucket_name,
                object_name=object_name,
            )

        if response_error.code in ["NoSuchBucket", "RetryHead"]:
            self._region_map.pop(bucket_name, None)

        raise response_error

    async def _execute(
        self,
        method,
        bucket_name=None,
        object_name=None,
        body=None,
        headers=None,
        query_params=None,
        session=None,
    ):
        """Execute HTTP request."""
        region = await self._get_region(bucket_name, None)

        try:
            if session is None:
                async with aiohttp.ClientSession() as session:
                    response = await self._url_open(
                        method,
                        region,
                        bucket_name=bucket_name,
                        object_name=object_name,
                        body=body,
                        headers=headers,
                        query_params=query_params,
                        session=session,
                    )
                    return response
            else:
                response = await self._url_open(
                    method,
                    region,
                    bucket_name=bucket_name,
                    object_name=object_name,
                    body=body,
                    headers=headers,
                    query_params=query_params,
                    session=session,
                )
                return response
        except S3Error as exc:
            if exc.code != "RetryHead":
                raise

        # Retry only once on RetryHead error.
        try:
            if session is None:
                async with aiohttp.ClientSession() as session:
                    response = await self._url_open(
                        method,
                        region,
                        bucket_name=bucket_name,
                        object_name=object_name,
                        body=body,
                        headers=headers,
                        query_params=query_params,
                        session=session,
                    )
                    return response
            else:
                response = await self._url_open(
                    method,
                    region,
                    bucket_name=bucket_name,
                    object_name=object_name,
                    body=body,
                    headers=headers,
                    query_params=query_params,
                    session=session,
                )
                return response
        except S3Error as exc:
            if exc.code != "RetryHead":
                raise

            code, message = self._handle_redirect_response(
                method,
                bucket_name,
                exc.response,
            )
            raise exc.copy(code, message)

    async def _get_region(self, bucket_name, region):
        """
        Return region of given bucket either from region cache or set in
        constructor.
        """

        if region:
            # Error out if region does not match with region passed via
            # constructor.
            if self._base_url.region and self._base_url.region != region:
                raise ValueError(
                    "region must be {0}, but passed {1}".format(
                        self._base_url.region,
                        region,
                    ),
                )
            return region

        if self._base_url.region:
            return self._base_url.region

        if not bucket_name or not self._provider:
            return "us-east-1"

        region = self._region_map.get(bucket_name)
        if region:
            return region

        # Execute GetBucketLocation REST API to get region of the bucket.
        async with aiohttp.ClientSession() as session:
            response = await self._url_open(
                "GET",
                "us-east-1",
                bucket_name=bucket_name,
                query_params={"location": ""},
                session=session,
            )

            element = ET.fromstring(await response.text())

        if not element.text:
            region = "us-east-1"
        elif element.text == "EU":
            region = "eu-west-1"
        else:
            region = element.text

        self._region_map[bucket_name] = region
        return region

    def set_app_info(self, app_name, app_version):
        """
        Set your application name and version to user agent header.

        :param app_name: Application name.
        :param app_version: Application version.

        Example::
            client.set_app_info('my_app', '1.0.2')
        """
        if not (app_name and app_version):
            raise ValueError("Application name/version cannot be empty.")

        self._user_agent = "{0} {1}/{2}".format(
            _DEFAULT_USER_AGENT,
            app_name,
            app_version,
        )

    def enable_accelerate_endpoint(self):
        """Enables accelerate endpoint for Amazon S3 endpoint."""
        self._base_url.accelerate_host_flag = True

    def disable_accelerate_endpoint(self):
        """Disables accelerate endpoint for Amazon S3 endpoint."""
        self._base_url.accelerate_host_flag = False

    def enable_dualstack_endpoint(self):
        """Enables dualstack endpoint for Amazon S3 endpoint."""
        self._base_url.dualstack_host_flag = True

    def disable_dualstack_endpoint(self):
        """Disables dualstack endpoint for Amazon S3 endpoint."""
        self._base_url.dualstack_host_flag = False

    def enable_virtual_style_endpoint(self):
        """Enables virtual style endpoint."""
        self._base_url.virtual_style_flag = True

    def disable_virtual_style_endpoint(self):
        """Disables virtual style endpoint."""
        self._base_url.virtual_style_flag = False

    async def select_object_content(self, bucket_name, object_name, request):
        """
        Select content of an object by SQL expression.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param request: :class:`SelectRequest <SelectRequest>` object.
        :return: A reader contains requested records and progress information
        as :class:`async_generator <async_generator>` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.select import (CSVInputSerialization,
            CSVOutputSerialization, SelectRequest)
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                result = await client.select_object_content(
                    "my-bucket",
                    "my-object.csv",
                    SelectRequest(
                        "select * from s3object",
                        CSVInputSerialization(),
                        CSVOutputSerialization(),
                        request_progress=True,
                    ),
                )
                print('data:')
                async for data in result.stream():
                    print(data.decode())
                print('status:',result.stats())

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        if not isinstance(request, SelectRequest):
            raise ValueError("request must be SelectRequest type")
        body = marshal(request)
        session = aiohttp.ClientSession()
        response = await self._execute(
            "POST",
            bucket_name=bucket_name,
            object_name=object_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params={"select": "", "select-type": "2"},
            session=session,
        )
        return SelectObjectReader(response, session)

    async def make_bucket(
        self, bucket_name, location="us-east-1", object_lock=False
    ) -> None:
        """
        Create a bucket with region and object lock.

        :param bucket_name: Name of the bucket.
        :param location: Region in which the bucket will be created.
        :param object_lock: Flag to set object-lock feature.

        Examples::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True
            )

            async def main():
                # Create bucket.
                print('example one')
                await client.make_bucket("my-bucket1")

                # Create bucket on specific region.
                print('example two')
                await client.make_bucket("my-bucket2", "us-east-1")

                # Create bucket with object-lock feature on specific region.
                print('example three')
                await client.make_bucket("my-bucket3", "us-east-1",
                object_lock=True)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name, True)
        if self._base_url.region:
            # Error out if region does not match with region passed via
            # constructor.
            if location and self._base_url.region != location:
                raise ValueError(
                    f"region must be {self._base_url.region}, "
                    f"but {location} was passed"
                )
        location = self._base_url.region or location or "us-east-1"
        headers = {"x-amz-bucket-object-lock-enabled": "true"} if object_lock else None

        body = None
        if location != "us-east-1":
            element = Element("CreateBucketConfiguration")
            SubElement(element, "LocationConstraint", location)
            body = getbytes(element)
        async with aiohttp.ClientSession() as session:
            await self._url_open(
                "PUT",
                location,
                bucket_name=bucket_name,
                body=body,
                headers=headers,
                session=session,
            )
        self._region_map[bucket_name] = location

    async def list_buckets(self) -> list:
        """
        List information of all accessible buckets.

        :return: List of :class:`Bucket <Bucket>` object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                buckets = await client.list_buckets()
                for bucket in buckets:
                    print(bucket.name, bucket.creation_date)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        async with aiohttp.ClientSession() as session:
            response = await self._execute("GET", session=session)
            result = unmarshal(ListAllMyBucketsResult, await response.text())
            return result.buckets

    async def bucket_exists(self, bucket_name):
        """
        Check if a bucket exists.

        :param bucket_name: Name of the bucket.
        :return: True if the bucket exists.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                result = await client.bucket_exists("my-bucket")
                if result:
                    print("my-bucket exists")
                else:
                    print("my-bucket does not exist")

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        try:
            await self._execute("HEAD", bucket_name)
            return True
        except S3Error as exc:
            if exc.code != "NoSuchBucket":
                raise
        return False

    async def remove_bucket(self, bucket_name):
        """
        Remove an empty bucket.

        :param bucket_name: Name of the bucket.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.remove_bucket("my-bucket")

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        await self._execute("DELETE", bucket_name)
        self._region_map.pop(bucket_name, None)

    async def get_bucket_policy(self, bucket_name):
        """
        Get bucket policy configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :return: Bucket policy configuration as JSON string.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                policy = await client.get_bucket_policy("my-bucket")
                print(policy)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "GET", bucket_name, query_params={"policy": ""}, session=session
            )
            return await response.text()

    async def delete_bucket_policy(self, bucket_name):
        """
        Delete bucket policy configuration of a bucket.

        :param bucket_name: Name of the bucket.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.delete_bucket_policy("my-bucket")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        await self._execute("DELETE", bucket_name, query_params={"policy": ""})

    async def set_bucket_policy(self, bucket_name, policy):
        """
        Set bucket policy configuration to a bucket.

        :param bucket_name: Name of the bucket.
        :param policy: Bucket policy configuration as JSON string.

        Example::
            import json
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # Example anonymous read-only bucket policy.
                print('example one')
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                            "Resource": "arn:aws:s3:::my-bucket",
                        },
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": "s3:GetObject",
                            "Resource": "arn:aws:s3:::my-bucket/*",
                        },
                    ],
                }
                await client.set_bucket_policy("my-bucket", json.dumps(policy))

                # Example anonymous read-write bucket policy.
                print('example two')
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": [
                                "s3:GetBucketLocation",
                                "s3:ListBucket",
                                "s3:ListBucketMultipartUploads",
                            ],
                            "Resource": "arn:aws:s3:::my-bucket",
                        },
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": [
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:DeleteObject",
                                "s3:ListMultipartUploadParts",
                                "s3:AbortMultipartUpload",
                            ],
                            "Resource": "arn:aws:s3:::my-bucket/images/*",
                        },
                    ],
                }
                await client.set_bucket_policy("my-bucket", json.dumps(policy))

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        is_valid_policy_type(policy)
        await self._execute(
            "PUT",
            bucket_name,
            body=policy,
            headers={"Content-MD5": md5sum_hash(policy)},
            query_params={"policy": ""},
        )

    async def get_bucket_notification(self, bucket_name):
        """
        Get notification configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :return: :class:`NotificationConfig <NotificationConfig>` object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                config = await client.get_bucket_notification("my-bucket")
                print(config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "GET", bucket_name, query_params={"notification": ""}, session=session
            )
            return unmarshal(NotificationConfig, await response.text())

    async def set_bucket_notification(self, bucket_name, config):
        """
        Set notification configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :param config: class:`NotificationConfig <NotificationConfig>` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.notificationconfig import (NotificationConfig,
            PrefixFilterRule, QueueConfig)
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            config = NotificationConfig(
                queue_config_list=[
                    QueueConfig(
                        "QUEUE-ARN-OF-THIS-BUCKET",
                        ["s3:ObjectCreated:*"],
                        config_id="1",
                        prefix_filter_rule=PrefixFilterRule("abc"),
                    ),
                ],
            )

            async def main():
                await client.set_bucket_notification("my-bucket", config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        if not isinstance(config, NotificationConfig):
            raise ValueError("config must be NotificationConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params={"notification": ""},
        )

    async def delete_bucket_notification(self, bucket_name):
        """
        Delete notification configuration of a bucket. On success, S3 service
        stops notification of events previously set of the bucket.

        :param bucket_name: Name of the bucket.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.delete_bucket_notification("my-bucket")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        await self.set_bucket_notification(bucket_name, NotificationConfig())

    async def set_bucket_encryption(self, bucket_name, config):
        """
        Set encryption configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :param config: :class:`SSEConfig <SSEConfig>` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.sseconfig import Rule, SSEConfig
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.set_bucket_encryption(
                    "my-bucket", SSEConfig(Rule.new_sse_s3_rule()),
                )

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        if not isinstance(config, SSEConfig):
            raise ValueError("config must be SSEConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params={"encryption": ""},
        )

    async def get_bucket_encryption(self, bucket_name):
        """
        Get encryption configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :return: :class:`SSEConfig <SSEConfig>` object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                config = await client.get_bucket_encryption("my-bucket")
                print(config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        try:
            async with aiohttp.ClientSession() as session:
                response = await self._execute(
                    "GET", bucket_name, query_params={"encryption": ""}, session=session
                )
                return unmarshal(SSEConfig, await response.text())
        except S3Error as exc:
            if exc.code != "ServerSideEncryptionConfigurationNotFoundError":
                raise
        return None

    async def delete_bucket_encryption(self, bucket_name):
        """
        Delete encryption configuration of a bucket.

        :param bucket_name: Name of the bucket.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.delete_bucket_encryption("my-bucket")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        try:
            await self._execute(
                "DELETE",
                bucket_name,
                query_params={"encryption": ""},
            )
        except S3Error as exc:
            if exc.code != "ServerSideEncryptionConfigurationNotFoundError":
                raise

    async def listen_bucket_notification(
        self,
        bucket_name,
        prefix="",
        suffix="",
        events=("s3:ObjectCreated:*", "s3:ObjectRemoved:*", "s3:ObjectAccessed:*"),
    ):
        """
        Listen events of object prefix and suffix of a bucket. Caller should
        iterate returned iterator to read new events.

        :param bucket_name: Name of the bucket.
        :param prefix: Listen events of object starts with prefix.
        :param suffix: Listen events of object ends with suffix.
        :param events: Events to listen.
        :return: Iterator of event records as :dict:.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                events = await client.listen_bucket_notification(
                    "my-bucket",
                    prefix="my-prefix/",
                    events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
                )
                async for event in events:
                    print('event:',event)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        if self._base_url.is_aws_host:
            raise ValueError(
                "ListenBucketNotification API is not supported in Amazon S3",
            )

        return AsyncEventIterable(
            await self._execute(
                "GET",
                bucket_name,
                query_params={
                    "prefix": prefix or "",
                    "suffix": suffix or "",
                    "events": events,
                },
            ),
        )

    async def set_bucket_versioning(self, bucket_name, config):
        """
        Set versioning configuration to a bucket.

        :param bucket_name: Name of the bucket.
        :param config: :class:`VersioningConfig <VersioningConfig>`.

        Example::
            from miniopy_async import Minio
            from miniopy_async.commonconfig import ENABLED
            from miniopy_async.versioningconfig import VersioningConfig
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.set_bucket_versioning("my-bucket",
                VersioningConfig(ENABLED))

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        if not isinstance(config, VersioningConfig):
            raise ValueError("config must be VersioningConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params={"versioning": ""},
        )

    async def get_bucket_versioning(self, bucket_name):
        """
        Get versioning configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :return: :class:`VersioningConfig <VersioningConfig>`.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                config = await client.get_bucket_versioning("my-bucket")
                print(config.status)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "GET", bucket_name, query_params={"versioning": ""}, session=session
            )
            return unmarshal(VersioningConfig, await response.text())

    # FIXME: Broken, do not use this function
    async def fput_object(
        self,
        bucket_name,
        object_name,
        file_path,
        content_type="application/octet-stream",
        metadata=None,
        sse=None,
        progress=False,
        part_size=0,
        num_parallel_uploads=3,
        tags=None,
        retention=None,
        legal_hold=False,
    ):
        """
        Uploads data from a file to an object in a bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param file_path: Name of file to upload.
        :param content_type: Content type of the object.
        :param metadata: Any additional metadata to be uploaded along
            with your PUT request.
        :param sse: Server-side encryption.
        :param progress: Flag to set whether to show progress.
        :param part_size: Multipart part size
        :param num_parallel_uploads: Number of parallel uploads.
        :param tags: :class:`Tags` for the object.
        :param retention: :class:`Retention` configuration object.
        :param legal_hold: Flag to set legal hold for the object.
        :return: :class:`ObjectWriteResult` object.

        Example::
            from datetime import datetime, timedelta
            from miniopy_async import Minio
            from miniopy_async.commonconfig import GOVERNANCE, Tags
            from miniopy_async.retention import Retention
            from miniopy_async.sse import SseCustomerKey, SseKMS, SseS3
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # Upload data.
                print("example one")
                await client.fput_object(
                    "my-bucket", "my-object1", "my-filename",
                )

                # Upload data with content-type.
                print("example two")
                await client.fput_object(
                    "my-bucket", "my-object2", "my-filename",
                    content_type="application/octet-stream",
                )

                # Upload data with metadata.
                print("example three")
                await client.fput_object(
                    "my-bucket", "my-object3", "my-filename",
                    metadata={"Content-Type": "application/octet-stream"},
                )

                # Upload data with customer key type of server-side encryption.
                print("example four")
                await client.fput_object(
                    "my-bucket", "my-object4", "my-filename",
                    sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
                )

                # Upload data with KMS type of server-side encryption.
                print("example five")
                await client.fput_object(
                    "my-bucket", "my-object5", "my-filename",
                    sse=SseKMS("KMS-KEY-ID", {"Key1": "Value1", "Key2":
                    "Value2"}),
                )

                # Upload data with S3 type of server-side encryption.
                print("example six")
                await client.fput_object(
                    "my-bucket", "my-object6", "my-filename",
                    sse=SseS3(),
                )

                # Upload data with tags, retention and legal-hold.
                print("example seven")
                date = datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0,
                ) + timedelta(days=30)
                tags = Tags(for_object=True)
                tags["User"] = "jsmith"
                await client.fput_object(
                    "my-bucket", "my-object7", "my-filename",
                    tags=tags,
                    retention=Retention(GOVERNANCE, date),
                    legal_hold=True,
                )

                # Upload data with showing progress status.
                print("example eight")
                result = await client.fput_object(
                    "my-bucket", "my-object8", "my-filename", progress=True
                )

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """

        file_size = os.stat(file_path).st_size
        with open(file_path, "rb") as file_data:
            return await self.put_object(
                bucket_name,
                object_name,
                file_data,
                file_size,
                content_type=content_type,
                metadata=metadata,
                sse=sse,
                progress=progress,
                part_size=part_size,
                num_parallel_uploads=num_parallel_uploads,
                tags=tags,
                retention=retention,
                legal_hold=legal_hold,
            )

    async def fget_object(
        self,
        bucket_name,
        object_name,
        file_path,
        request_headers=None,
        ssec=None,
        version_id=None,
        extra_query_params=None,
        tmp_file_path=None,
    ):
        """
        Downloads data of an object to file.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param file_path: Name of file to download.
        :param request_headers: Any additional headers to be added with GET
                                request.
        :param ssec: Server-side encryption customer key.
        :param version_id: Version-ID of the object.
        :param extra_query_params: Extra query parameters for advanced usage.
        :param tmp_file_path: Path to a temporary file.
        :return: Object information.

        Example::
            from miniopy_async import Minio
            from miniopy_async.sse import SseCustomerKey
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # Download data of an object.
                print("example one")
                await client.fget_object("my-bucket", "my-object",
                "my-filename")

                # Download data of an object of version-ID.
                print("example two")
                await client.fget_object(
                    "my-bucket", "my-object", "my-filename",
                    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
                )

                # Download data of an SSE-C encrypted object.
                print("example three")
                await client.fget_object(
                    "my-bucket", "my-object", "my-filename",
                    ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
                )

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)

        if os.path.isdir(file_path):
            raise ValueError(f"file {file_path} is a directory")

        # Create top level directory if needed.
        makedirs(os.path.dirname(file_path))

        stat = await self.stat_object(
            bucket_name,
            object_name,
            ssec,
            version_id=version_id,
        )

        # Write to a temporary file "file_path.part.minio" before saving.
        tmp_file_path = tmp_file_path or file_path + "." + stat.etag + ".part.minio"
        try:
            tmp_file_stat = os.stat(tmp_file_path)
        except IOError:
            tmp_file_stat = None  # Ignore this error.
        offset = tmp_file_stat.st_size if tmp_file_stat else 0
        if offset > stat.size:
            os.remove(tmp_file_path)
            offset = 0

        response = None
        try:
            async with aiohttp.ClientSession() as session:
                response = await self.get_object(
                    bucket_name,
                    object_name,
                    session,
                    offset=offset,
                    request_headers=request_headers,
                    ssec=ssec,
                    version_id=version_id,
                    extra_query_params=extra_query_params,
                )
                async with aiofile.async_open(tmp_file_path, "wb") as tmp_file:
                    async for data in response.content.iter_chunked(n=1024 * 1024):
                        await tmp_file.write(data)
                if os.path.exists(file_path):
                    os.remove(file_path)  # For windows compatibility.
                os.rename(tmp_file_path, file_path)
                return stat
        finally:
            pass

    async def get_object(
        self,
        bucket_name,
        object_name,
        session,
        offset=0,
        length=0,
        request_headers=None,
        ssec=None,
        version_id=None,
        extra_query_params=None,
    ):
        """
        Get data of an object. Returned response should be closed after use to
        release network resources. To reuse the connection, it's required to
        call `response.release()` explicitly.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param session: :class:`aiohttp.ClientSession()` object.
        :param offset: Start byte position of object data.
        :param length: Number of bytes of object data from offset.
        :param request_headers: Any additional headers to be added with GET
                                request.
        :param ssec: Server-side encryption customer key.
        :param version_id: Version-ID of the object.
        :param extra_query_params: Extra query parameters for advanced usage.
        :return: :class:`aiohttp.client_reqrep.ClientResponse` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.sse import SseCustomerKey
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # Get data of an object.
                print('example one')
                async with aiohttp.ClientSession() as session:
                    response = await client.get_object("my-bucket", "my-object", session)
                    # Read data from response.

                # Get data of an object from offset and length.
                print('example two')
                async with aiohttp.ClientSession() as session:
                    response = await client.get_object(
                        "my-bucket", "my-object", session, offset=512, length=1024,
                    )
                    # Read data from response.

                # Get data of an object of version-ID.
                print('example three')
                async with aiohttp.ClientSession() as session:
                    response = await client.get_object(
                        "my-bucket", "my-object", sessioin
                        version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
                    )
                    # Read data from response.

                # Get data of an SSE-C encrypted object.
                print('example four')
                async with aiohttp.ClientSession() as session:
                    response = await client.get_object(
                        "my-bucket", "my-object", session
                        ssec=SseCustomerKey(
                        b"32byteslongsecretkeymustprovided"),
                    )
                    # Read data from response.

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        check_ssec(ssec)

        headers = ssec.headers() if ssec else {}
        headers.update(request_headers or {})

        if offset or length:
            headers["Range"] = "bytes={}-{}".format(
                offset, offset + length - 1 if length else ""
            )

        if version_id:
            extra_query_params = extra_query_params or {}
            extra_query_params["versionId"] = version_id

        return await self._execute(
            "GET",
            bucket_name,
            object_name,
            headers=headers,
            query_params=extra_query_params,
            session=session,
        )

    async def copy_object(
        self,
        bucket_name,
        object_name,
        source,
        sse=None,
        metadata=None,
        tags=None,
        retention=None,
        legal_hold=False,
        metadata_directive=None,
        tagging_directive=None,
    ):
        """
        Create an object by server-side copying data from another object.
        In this API maximum supported source object size is 5GiB.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param source: :class:`CopySource` object.
        :param sse: Server-side encryption of destination object.
        :param metadata: Any user-defined metadata to be copied along with
                         destination object.
        :param tags: Tags for destination object.
        :param retention: :class:`Retention` configuration object.
        :param legal_hold: Flag to set legal hold for destination object.
        :param metadata_directive: Directive used to handle user metadata for
                                   destination object.
        :param tagging_directive: Directive used to handle tags for destination
                                   object.
        :return: :class:`ObjectWriteResult <ObjectWriteResult>` object.

        Example::
            from datetime import datetime, timezone
            from miniopy_async import Minio
            from miniopy_async.commonconfig import REPLACE, CopySource
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # copy an object from a bucket to another.
                print("example one")
                result = await client.copy_object(
                    "my-job-bucket",
                    "my-copied-object1",
                    CopySource("my-bucket", "my-object"),
                )
                print(result.object_name, result.version_id)

                # copy an object with condition.
                print("example two")
                result = await client.copy_object(
                    "my-job-bucket",
                    "my-copied-object2",
                    CopySource(
                        "my-bucket",
                        "my-object",
                        modified_since=datetime(2014, 4, 1,
                        tzinfo=timezone.utc),
                    ),
                )
                print(result.object_name, result.version_id)

                # copy an object from a bucket with replacing metadata.
                print("example three")
                metadata = {"Content-Type": "application/octet-stream"}
                result = await client.copy_object(
                    "my-job-bucket",
                    "my-copied-object3",
                    CopySource("my-bucket", "my-object"),
                    metadata=metadata,
                    metadata_directive=REPLACE,
                )
                print(result.object_name, result.version_id)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        if not isinstance(source, CopySource):
            raise ValueError("source must be CopySource type")
        check_sse(sse)
        if tags is not None and not isinstance(tags, Tags):
            raise ValueError("tags must be Tags type")
        if retention is not None and not isinstance(retention, Retention):
            raise ValueError("retention must be Retention type")
        if metadata_directive is not None and metadata_directive not in [COPY, REPLACE]:
            raise ValueError(
                "metadata directive must be {0} or {1}".format(COPY, REPLACE),
            )
        if tagging_directive is not None and tagging_directive not in [COPY, REPLACE]:
            raise ValueError(
                "tagging directive must be {0} or {1}".format(COPY, REPLACE),
            )

        size = -1
        if source.offset is None and source.length is None:
            stat = await self.stat_object(
                source.bucket_name,
                source.object_name,
                version_id=source.version_id,
                ssec=source.ssec,
            )
            size = stat.size

        if (
            source.offset is not None
            or source.length is not None
            or size > MAX_PART_SIZE
        ):
            if metadata_directive == COPY:
                raise ValueError(
                    "COPY metadata directive is not applicable to source "
                    "object size greater than 5 GiB",
                )
            if tagging_directive == COPY:
                raise ValueError(
                    "COPY tagging directive is not applicable to source "
                    "object size greater than 5 GiB"
                )
            return await self.compose_object(
                bucket_name,
                object_name,
                ComposeSource.of(source),
                sse=sse,
                metadata=metadata,
                tags=tags,
                retention=retention,
                legal_hold=legal_hold,
            )

        headers = genheaders(metadata, sse, tags, retention, legal_hold)
        if metadata_directive:
            headers["x-amz-metadata-directive"] = metadata_directive
        if tagging_directive:
            headers["x-amz-tagging-directive"] = tagging_directive
        headers.update(source.gen_copy_headers())
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "PUT",
                bucket_name,
                object_name=object_name,
                headers=headers,
                session=session,
            )
            etag, last_modified = parse_copy_object(await response.text())
            return ObjectWriteResult(
                bucket_name,
                object_name,
                response.headers.get("x-amz-version-id"),
                etag,
                response.headers,
                last_modified=last_modified,
            )

    async def _calc_part_count(self, sources):
        """Calculate part count."""
        object_size = 0
        part_count = 0
        i = 0
        for src in sources:
            i += 1
            stat = await self.stat_object(
                src.bucket_name,
                src.object_name,
                version_id=src.version_id,
                ssec=src.ssec,
            )
            src.build_headers(stat.size, stat.etag)
            size = stat.size
            if src.length is not None:
                size = src.length
            elif src.offset is not None:
                size -= src.offset

            if size < MIN_PART_SIZE and len(sources) != 1 and i != len(sources):
                raise ValueError(
                    "source {0}/{1}: size {2} must be greater than {3}".format(
                        src.bucket_name,
                        src.object_name,
                        size,
                        MIN_PART_SIZE,
                    ),
                )

            object_size += size
            if object_size > MAX_MULTIPART_OBJECT_SIZE:
                raise ValueError(
                    "destination object size must be less than {0}".format(
                        MAX_MULTIPART_OBJECT_SIZE,
                    ),
                )

            if size > MAX_PART_SIZE:
                count = int(size / MAX_PART_SIZE)
                last_part_size = size - (count * MAX_PART_SIZE)
                if last_part_size > 0:
                    count += 1
                else:
                    last_part_size = MAX_PART_SIZE
                if (
                    last_part_size < MIN_PART_SIZE
                    and len(sources) != 1
                    and i != len(sources)
                ):
                    raise ValueError(
                        (
                            "source {0}/{1}: for multipart split upload of "
                            "{2}, last part size is less than {3}"
                        ).format(
                            src.bucket_name,
                            src.object_name,
                            size,
                            MIN_PART_SIZE,
                        ),
                    )
                part_count += count
            else:
                part_count += 1

        if part_count > MAX_MULTIPART_COUNT:
            raise ValueError(
                (
                    "Compose sources create more than allowed multipart " "count {0}"
                ).format(MAX_MULTIPART_COUNT),
            )
        return part_count

    async def _upload_part_copy(
        self, bucket_name, object_name, upload_id, part_number, headers
    ):
        """Execute UploadPartCopy S3 API."""
        query_params = {
            "partNumber": str(part_number),
            "uploadId": upload_id,
        }
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "PUT",
                bucket_name,
                object_name,
                headers=headers,
                query_params=query_params,
                session=session,
            )
            return parse_copy_object(await response.text())

    async def compose_object(  # pylint: disable=too-many-branches
        self,
        bucket_name,
        object_name,
        sources,
        sse=None,
        metadata=None,
        tags=None,
        retention=None,
        legal_hold=False,
    ):
        """
        Create an object by combining data from different source objects using
        server-side copy.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param sources: List of :class:`ComposeSource` object.
        :param sse: Server-side encryption of destination object.
        :param metadata: Any user-defined metadata to be copied along with
                         destination object.
        :param tags: Tags for destination object.
        :param retention: :class:`Retention` configuration object.
        :param legal_hold: Flag to set legal hold for destination object.
        :return: :class:`ObjectWriteResult <ObjectWriteResult>` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.commonconfig import ComposeSource
            from miniopy_async.sse import SseS3
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            # Each part must larger than 5MB
            sources = [
                ComposeSource("my-job-bucket", "my-object-part-one"),
                ComposeSource("my-job-bucket", "my-object-part-two"),
                ComposeSource("my-job-bucket", "my-object-part-three"),
            ]

            async def main():
                # Create my-bucket/my-object by combining source object
                # list.
                print('example one')
                result = await client.compose_object("my-bucket",
                "my-object", sources)
                print(result.object_name, result.version_id)

                # Create my-bucket/my-object with user metadata by combining
                # source object list.
                print('example two')
                result = await client.compose_object(
                    "my-bucket",
                    "my-object",
                    sources,
                    metadata={"Content-Type": "application/octet-stream"},
                )
                print(result.object_name, result.version_id)

                # Create my-bucket/my-object with user metadata and
                # server-side encryption by combining source object list.
                print('example three')
                result = await client.compose_object(
                    "my-bucket",
                    "my-object",
                    sources,
                    sse=SseS3()
                )
                print(result.object_name, result.version_id)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        if not isinstance(sources, (list, tuple)) or not sources:
            raise ValueError("sources must be non-empty list or tuple type")
        i = 0
        for src in sources:
            if not isinstance(src, ComposeSource):
                raise ValueError(
                    "sources[{0}] must be ComposeSource type".format(i),
                )
            i += 1
        check_sse(sse)
        if tags is not None and not isinstance(tags, Tags):
            raise ValueError("tags must be Tags type")
        if retention is not None and not isinstance(retention, Retention):
            raise ValueError("retention must be Retention type")

        part_count = await self._calc_part_count(sources)
        if part_count == 1 and sources[0].offset is None and sources[0].length is None:
            return await self.copy_object(
                bucket_name,
                object_name,
                CopySource.of(sources[0]),
                sse=sse,
                metadata=metadata,
                tags=tags,
                retention=retention,
                legal_hold=legal_hold,
                metadata_directive=REPLACE if metadata else None,
                tagging_directive=REPLACE if tags else None,
            )

        headers = genheaders(metadata, sse, tags, retention, legal_hold)
        upload_id = await self._create_multipart_upload(
            bucket_name,
            object_name,
            headers,
        )
        ssec_headers = sse.headers() if isinstance(sse, SseCustomerKey) else {}
        try:
            part_number = 0
            total_parts = []
            for src in sources:
                size = src.object_size
                if src.length is not None:
                    size = src.length
                elif src.offset is not None:
                    size -= src.offset
                offset = src.offset or 0
                headers = src.headers
                headers.update(ssec_headers)
                if size <= MAX_PART_SIZE:
                    part_number += 1
                    if src.length is not None:
                        headers["x-amz-copy-source-range"] = "bytes={0}-{1}".format(
                            offset, offset + src.length - 1
                        )
                    elif src.offset is not None:
                        headers["x-amz-copy-source-range"] = "bytes={0}-{1}".format(
                            offset, offset + size - 1
                        )
                    etag, _ = await self._upload_part_copy(
                        bucket_name,
                        object_name,
                        upload_id,
                        part_number,
                        headers,
                    )
                    total_parts.append(Part(part_number, etag))
                    continue
                while size > 0:
                    part_number += 1
                    start_bytes = offset
                    end_bytes = start_bytes + MAX_PART_SIZE
                    if size < MAX_PART_SIZE:
                        end_bytes = start_bytes + size
                    headers_copy = headers.copy()
                    headers_copy["x-amz-copy-source-range"] = "bytes={0}-{1}".format(
                        start_bytes, end_bytes
                    )
                    etag, _ = await self._upload_part_copy(
                        bucket_name,
                        object_name,
                        upload_id,
                        part_number,
                        headers_copy,
                    )
                    total_parts.append(Part(part_number, etag))
                    offset = start_bytes
                    size -= end_bytes - start_bytes
            result = await self._complete_multipart_upload(
                bucket_name,
                object_name,
                upload_id,
                total_parts,
            )
            return ObjectWriteResult(
                result.bucket_name,
                result.object_name,
                result.version_id,
                result.etag,
                result.http_headers,
                location=result.location,
            )
        except Exception as exc:
            if upload_id:
                await self._abort_multipart_upload(
                    bucket_name,
                    object_name,
                    upload_id,
                )
            raise exc

    async def _abort_multipart_upload(self, bucket_name, object_name, upload_id):
        """Execute AbortMultipartUpload S3 API."""
        await self._execute(
            "DELETE",
            bucket_name,
            object_name,
            query_params={"uploadId": upload_id},
        )

    async def _complete_multipart_upload(
        self, bucket_name, object_name, upload_id, parts
    ) -> CompleteMultipartUploadResult:
        """Execute CompleteMultipartUpload S3 API."""
        element = Element("CompleteMultipartUpload")
        for part in parts:
            tag = SubElement(element, "Part")
            SubElement(tag, "PartNumber", str(part.part_number))
            SubElement(tag, "ETag", '"' + part.etag + '"')
        body = getbytes(element)
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "POST",
                bucket_name,
                object_name,
                body=body,
                headers={
                    "Content-Type": "application/xml",
                    "Content-MD5": md5sum_hash(body),
                },
                query_params={"uploadId": upload_id},
                session=session,
            )
            return await CompleteMultipartUploadResult.from_async_response(response)

    async def _create_multipart_upload(self, bucket_name, object_name, headers):
        """Execute CreateMultipartUpload S3 API."""
        if not headers.get("Content-Type"):
            headers["Content-Type"] = "application/octet-stream"
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "POST",
                bucket_name,
                object_name,
                headers=headers,
                query_params={"uploads": ""},
                session=session,
            )
            element = ET.fromstring(await response.text())
        return findtext(element, "UploadId")

    async def _put_object(
        self, bucket_name, object_name, data, headers, query_params=None, progress=None
    ):
        """Execute PutObject S3 API."""
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "PUT",
                bucket_name,
                object_name,
                body=data,
                headers=headers,
                query_params=query_params,
                session=session,
            )
            if progress:
                progress.update(len(data))
            return ObjectWriteResult(
                bucket_name,
                object_name,
                response.headers.get("x-amz-version-id"),
                response.headers.get("etag").replace('"', ""),
                response.headers,
            )

    async def _upload_part(
        self,
        bucket_name,
        object_name,
        data,
        headers,
        upload_id,
        part_number,
        progress=None,
    ):
        """Execute UploadPart S3 API."""
        query_params = {
            "partNumber": str(part_number),
            "uploadId": upload_id,
        }
        result = await self._put_object(
            bucket_name,
            object_name,
            data,
            headers,
            query_params=query_params,
            progress=progress,
        )
        return result.etag

    async def _upload_part_task(self, args, progress=None):
        """Upload_part task for ThreadPool."""
        return args[5], await self._upload_part(*args, progress=progress)

    async def put_object(
        self,
        bucket_name,
        object_name,
        data,
        length,
        content_type="application/octet-stream",
        metadata=None,
        sse=None,
        progress=False,
        part_size=0,
        num_parallel_uploads=3,
        tags=None,
        retention=None,
        legal_hold=False,
    ) -> ObjectWriteResult:
        """
        Uploads data from a stream to an object in a bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param data: An object having callable read() returning bytes object.
        :param length: Data size; -1 for unknown size and set valid part_size.
        :param content_type: Content type of the object.
        :param metadata: Any additional metadata to be uploaded along
            with your PUT request.
        :param sse: Server-side encryption.
        :param progress: Flag to set whether to show progress.
        :param part_size: Multipart part size.
        :param num_parallel_uploads: Number of parallel uploads.
        :param tags: :class:`Tags` for the object.
        :param retention: :class:`Retention` configuration object.
        :param legal_hold: Flag to set legal hold for the object.
        :return: :class:`ObjectWriteResult` object.

        Example::
            import io
            from datetime import datetime, timedelta
            from urllib.request import urlopen
            from miniopy_async import Minio
            from miniopy_async.commonconfig import GOVERNANCE, Tags
            from miniopy_async.retention import Retention
            from miniopy_async.sse import SseCustomerKey, SseKMS, SseS3
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # Upload data.
                print('example one')
                await client.put_object(
                    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
                )

                # Upload unknown sized data.
                print('example two')
                data = urlopen(
                    "https://raw.githubusercontent.com/hlf20010508/miniopy
                    -async/master/README.md",
                )
                await client.put_object(
                    "my-bucket", "my-object", data, length=-1,
                    part_size=10*1024*1024,
                )

                # Upload data with content-type.
                print('example three')
                await client.put_object(
                    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
                    content_type="application/csv",
                )

                # Upload data with metadata.
                print('example four')
                await client.put_object(
                    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
                    metadata={"Content-Type": "application/octet-stream"},
                )

                # Upload data with customer key type of server-side encryption.
                print('example five')
                await client.put_object(
                    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
                    sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
                )

                # Upload data with KMS type of server-side encryption.
                print('example six')
                await client.put_object(
                    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
                    sse=SseKMS("KMS-KEY-ID", {"Key1": "Value1", "Key2":
                    "Value2"}),
                )

                # Upload data with S3 type of server-side encryption.
                print('example seven')
                await client.put_object(
                    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
                    sse=SseS3(),
                )

                # Upload data with tags, retention and legal-hold.
                print('example eight')
                date = datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0,
                ) + timedelta(days=30)
                tags = Tags(for_object=True)
                tags["User"] = "jsmith"
                await client.put_object(
                    "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
                    tags=tags,
                    retention=Retention(GOVERNANCE, date),
                    legal_hold=True,
                )

                # Upload data with showing progress status.
                print('example nine')
                await client.put_object(
                    "transfer", "my-object", io.BytesIO(
                    b"helloworld"*2000000), 20000000, progress=True
                )

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        check_sse(sse)
        if tags is not None and not isinstance(tags, Tags):
            raise ValueError("tags must be Tags type")
        if retention is not None and not isinstance(retention, Retention):
            raise ValueError("retention must be Retention type")
        if not callable(getattr(data, "read")):
            raise ValueError("input data must have callable read()")
        part_size, part_count = get_part_info(length, part_size)
        if progress:
            progress = Progress(object_name, length)

        headers = genheaders(metadata, sse, tags, retention, legal_hold)
        headers["Content-Type"] = content_type or "application/octet-stream"

        object_size = length
        uploaded_size = 0
        part_number = 0
        one_byte = b""
        stop = False
        upload_id = None
        parts = []
        parallel_tasks = []

        try:
            while not stop:
                part_number += 1
                if part_count > 0:
                    if part_number == part_count:
                        part_size = object_size - uploaded_size
                        stop = True
                    part_data = await read_part_data(data, part_size)
                    if len(part_data) != part_size:
                        raise IOError(
                            (
                                "stream having not enough data;"
                                "expected: {0}, got: {1} bytes"
                            ).format(part_size, len(part_data))
                        )
                else:
                    part_data = await read_part_data(data, part_size + 1, one_byte)
                    # If part_data_size is less or equal to part_size,
                    # then we have reached last part.
                    if len(part_data) <= part_size:
                        part_count = part_number
                        stop = True
                    else:
                        one_byte = part_data[-1:]
                        part_data = part_data[:-1]

                uploaded_size += len(part_data)

                if part_count == 1:
                    return await self._put_object(
                        bucket_name,
                        object_name,
                        part_data,
                        headers,
                    )

                if not upload_id:
                    upload_id = await self._create_multipart_upload(
                        bucket_name,
                        object_name,
                        headers,
                    )

                args = (
                    bucket_name,
                    object_name,
                    part_data,
                    sse.headers() if isinstance(sse, SseCustomerKey) else None,
                    upload_id,
                    part_number,
                )
                if num_parallel_uploads and num_parallel_uploads > 1:
                    parallel_tasks.append(
                        asyncio.ensure_future(
                            self._upload_part_task(args, progress=progress)
                        )
                    )
                    if (
                        part_number % num_parallel_uploads == 0
                        or part_number == part_count
                    ):
                        parts.extend(
                            (
                                Part(number, etag)
                                for number, etag in await asyncio.gather(
                                    *parallel_tasks
                                )
                            )
                        )
                        parallel_tasks.clear()

                else:
                    etag = await self._upload_part(*args, progress=progress)
                    parts.append(Part(part_number, etag))

            result = await self._complete_multipart_upload(
                bucket_name,
                object_name,
                upload_id,
                parts,
            )
            return ObjectWriteResult(
                result.bucket_name,
                result.object_name,
                result.version_id,
                result.etag,
                result.http_headers,
                location=result.location,
            )
        except Exception as exc:
            if upload_id:
                await self._abort_multipart_upload(
                    bucket_name,
                    object_name,
                    upload_id,
                )
            raise exc

    def list_objects(
        self,
        bucket_name,
        prefix=None,
        recursive=False,
        start_after=None,
        include_user_meta=False,
        include_version=False,
        use_api_v1=False,
        use_url_encoding_type=True,
    ):
        """
        Lists object information of a bucket.

        :param bucket_name: Name of the bucket.
        :param prefix: Object name starts with prefix.
        :param recursive: List recursively than directory structure emulation.
        :param start_after: List objects after this key name.
        :param include_user_meta: MinIO specific flag to control to include
                                 user metadata.
        :param include_version: Flag to control whether include object
                                versions.
        :param use_api_v1: Flag to control to use ListObjectV1 S3 API or not.
        :param use_url_encoding_type: Flag to control whether URL encoding type
                                      to be used or not.
        :return: Iterator of :class:`Object <Object>`.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # List objects information.
                print('example one')
                objects = await client.list_objects("my-bucket")
                for obj in objects:
                    print('obj:',obj)

                async for obj in client.list_objects("my-bucket"):
                    print('obj:',obj)

                # List objects information whose names starts with "my/prefix/".
                print('example two')
                objects = await client.list_objects("my-bucket",
                prefix="my/prefix/")
                for obj in objects:
                    print('obj:',obj)

                # List objects information recursively.
                print('example three')
                objects = await client.list_objects("my-bucket", recursive=True)
                for obj in objects:
                    print('obj:',obj)

                # List objects information recursively whose names starts with
                # "my/prefix/".
                print('example four')
                objects = await client.list_objects(
                    "my-bucket", prefix="my/prefix/", recursive=True,
                )
                for obj in objects:
                    print('obj:',obj)

                # List objects information recursively after object name
                # "my/prefix/world/1".
                print('example five')
                objects = await client.list_objects(
                    "my-bucket", recursive=True,
                    start_after="my/prefix/world/1",
                )
                for obj in objects:
                    print('obj:',obj)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        return ListObjects(
            client=self,
            bucket_name=bucket_name,
            prefix=prefix,
            recursive=recursive,
            start_after=start_after,
            include_user_meta=include_user_meta,
            include_version=include_version,
            use_api_v1=use_api_v1,
            use_url_encoding_type=use_url_encoding_type,
        )

    async def stat_object(
        self,
        bucket_name,
        object_name,
        ssec=None,
        version_id=None,
        request_headers=None,
        extra_query_params=None,
    ):
        """
        Get object information and metadata of an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param ssec: Server-side encryption customer key.
        :param version_id: Version ID of the object.
        :param request_headers: Any additional headers to be added with GET request.
        :param extra_query_params: Extra query parameters for advanced usage.
        :return: :class:`Object <Object>`.

        Example::
            from miniopy_async import Minio
            from miniopy_async.sse import SseCustomerKey
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # Get object information.
                print('example one')
                result = await client.stat_object("my-bucket", "my-object")
                print(
                    "status: last-modified: {0}, size: {1}".format(
                        result.last_modified, result.size,
                    ),
                )

                # Get object information of version-ID.
                print('example two')
                result = await client.stat_object(
                    "my-bucket", "my-object",
                    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
                )
                print(
                    "status: last-modified: {0}, size: {1}".format(
                        result.last_modified, result.size,
                    ),
                )

                # Get SSE-C encrypted object information.
                print('example three')
                result = await client.stat_object(
                    "my-bucket", "my-object",
                    ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
                )
                print(
                    "status: last-modified: {0}, size: {1}".format(
                        result.last_modified, result.size,
                    ),
                )

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """

        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        check_ssec(ssec)

        headers = ssec.headers() if ssec else {}
        if request_headers:
            headers.update(request_headers)
        query_params = extra_query_params or {}
        query_params.update({"versionId": version_id} if version_id else {})
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "HEAD",
                bucket_name,
                object_name,
                headers=headers,
                query_params=query_params,
                session=session,
            )

            last_modified = response.headers.get("last-modified")
            if last_modified:
                last_modified = time.from_http_header(last_modified)

            return Object(
                bucket_name,
                object_name,
                last_modified=last_modified,
                etag=response.headers.get("etag", "").replace('"', ""),
                size=int(response.headers.get("content-length", "0")),
                content_type=response.headers.get("content-type"),
                metadata=response.headers,
                version_id=response.headers.get("x-amz-version-id"),
            )

    async def list_object_versions(self, bucket_name):
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "GET", bucket_name, query_params={"versions": ""}, session=session
            )
            return await response.text()

    async def remove_object(self, bucket_name, object_name, version_id=None):
        """
        Remove an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # Remove object.
                print('example one')
                await client.remove_object("my-bucket", "my-object")

                # Remove version of an object.
                print('example two')
                await client.remove_object(
                    "my-bucket", "my-object",
                    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
                )

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        await self._execute(
            "DELETE",
            bucket_name,
            object_name,
            query_params={"versionId": version_id} if version_id else None,
        )

    async def _delete_objects(
        self, bucket_name, delete_object_list, quiet=False, bypass_governance_mode=False
    ):
        """
        Delete multiple objects.

        :param bucket_name: Name of the bucket.
        :param delete_object_list: List of maximum 1000
            :class:`DeleteObject <DeleteObject>` object.
        :param quiet: quiet flag.
        :param bypass_governance_mode: Bypass Governance retention mode.
        :return: :class:`DeleteResult <DeleteResult>` object.
        """
        body = marshal(DeleteRequest(delete_object_list, quiet=quiet))
        headers = {"Content-MD5": md5sum_hash(body)}
        if bypass_governance_mode:
            headers["x-amz-bypass-governance-retention"] = "true"
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "POST",
                bucket_name,
                body=body,
                headers=headers,
                query_params={"delete": ""},
                session=session,
            )

            element = ET.fromstring(await response.text())
            return (
                DeleteResult([], [DeleteError.fromxml(element)])
                if element.tag.endswith("Error")
                else unmarshal(DeleteResult, await response.text())
            )

    # TODO Return asynchronous iterator for objects
    async def remove_objects(
        self, bucket_name, delete_object_list, bypass_governance_mode=False
    ):
        """
        Remove multiple objects.

        :param bucket_name: Name of the bucket.
        :param delete_object_list: An iterable containing
            :class:`DeleteObject <DeleteObject>` object.
        :param bypass_governance_mode: Bypass Governance retention mode.
        :return: An iterator containing :class:`DeleteError <DeleteError>`
            object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.deleteobjects import DeleteObject
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                # Remove list of objects.
                print('example one')
                errors = await client.remove_objects(
                    "my-bucket",
                    [
                        DeleteObject("my-object1"),
                        DeleteObject("my-object2"),
                        DeleteObject("my-object3",
                        "13f88b18-8dcd-4c83-88f2-8631fdb6250c"),
                    ],
                )
                for error in errors:
                    print("error occured when deleting object", error)

                # Remove a prefix recursively.
                print('example two')
                delete_object_list = [DeleteObject(obj.object_name)
                    for obj in await client.list_objects(
                        "my-bucket",
                        "my/prefix/",
                        recursive=True
                    )
                ]
                errors = await client.remove_objects("my-bucket",
                delete_object_list)
                for error in errors:
                    print("error occured when deleting object", error)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)

        # turn list like objects into an iterator.
        delete_object_list = itertools.chain(delete_object_list)

        while True:
            # get 1000 entries or whatever available.
            objects = [
                delete_object
                for _, delete_object in zip(
                    range(1000),
                    delete_object_list,
                )
            ]

            if not objects:
                return ()

            result = await self._delete_objects(
                bucket_name,
                objects,
                quiet=True,
                bypass_governance_mode=bypass_governance_mode,
            )

            return tuple(
                filter(lambda error: error.code != "NoSuchVersion", result.error_list)
            )

    async def get_presigned_url(
        self,
        method,
        bucket_name,
        object_name,
        expires=timedelta(days=7),
        response_headers=None,
        request_date=None,
        version_id=None,
        extra_query_params=None,
        change_host=None,
    ):
        """
        Get presigned URL of an object for HTTP method, expiry time and custom
        request parameters.

        :param method: HTTP method.
        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param expires: Expiry in seconds; defaults to 7 days.
        :param response_headers: Optional response_headers argument to
                                 specify response fields like date, size,
                                 type of file, data about server, etc.
        :param request_date: Optional request_date argument to
                             specify a different request date. Default is
                             current date.
        :param version_id: Version ID of the object.
        :param extra_query_params: Extra query parameters for advanced usage.
        :param change_host: Change the host for this presign temporaryly.
        This parameter
                            is for the circumstance in which your base url is
                            set with private IP address
                            such as 127.0.0.1 or 0.0.0.0 and you want to
                            create a url with public IP address.
        :return: URL string.

        Example::
            from datetime import timedelta
            from miniopy_async import Minio
            import asyncio

            async def main():
                client = Minio(
                    "play.min.io",
                    access_key="Q3AM3UQ867SPQQA43P2F",
                    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                    secure=True  # http for False, https for True
                )
                # Get presigned URL string to delete 'my-object' in
                # 'my-bucket' with one day expiry.
                print('example one')
                url = await client.get_presigned_url(
                    "DELETE",
                    "my-bucket",
                    "my-object",
                    expires=timedelta(days=1),
                )
                print('url:', url)

                # Get presigned URL string to upload 'my-object' in
                # 'my-bucket' with response-content-type as application/json
                # and one day expiry.
                print('example two')
                url = await client.get_presigned_url(
                    "PUT",
                    "my-bucket",
                    "my-object",
                    expires=timedelta(days=1),
                    response_headers={"response-content-type":
                    "application/json"},
                )
                print('url:', url)

                # Get presigned URL string to download 'my-object' in
                # 'my-bucket' with two hours expiry.
                print('example three')
                url = await client.get_presigned_url(
                    "GET",
                    "my-bucket",
                    "my-object",
                    expires=timedelta(hours=2),
                )
                print('url:', url)

                # Get presigned URL string to download 'my-object' in
                # 'my-bucket' with public IP address when using private IP
                address.
                client = Minio(
                    "127.0.0.1:9000",
                    access_key="your access key",
                    secret_key="you secret key",
                    secure=False  # http for False, https for True
                )

                print('example four')
                url = await client.get_presigned_url(
                    "GET",
                    "my-bucket",
                    "my-object",
                    change_host='https://YOURHOST:YOURPORT',
                )
                print('url:', url)


            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        if expires.total_seconds() < 1 or expires.total_seconds() > 604800:
            raise ValueError("expires must be between 1 second to 7 days")

        region = await self._get_region(bucket_name, None)
        query_params = extra_query_params or {}
        query_params.update({"versionId": version_id} if version_id else {})
        query_params.update(response_headers or {})
        creds = self._provider.retrieve() if self._provider else None
        if creds and creds.session_token:
            query_params["X-Amz-Security-Token"] = creds.session_token

        url = None
        if change_host:
            url = BaseURL(
                change_host,
                region,
            ).build(
                method,
                region,
                bucket_name=bucket_name,
                object_name=object_name,
                query_params=query_params,
            )
        else:
            url = self._base_url.build(
                method,
                region,
                bucket_name=bucket_name,
                object_name=object_name,
                query_params=query_params,
            )

        if creds:
            url = presign_v4(
                method,
                url,
                region,
                creds,
                request_date or time.utcnow(),
                int(expires.total_seconds()),
            )
        return urlunsplit(url)

    async def presigned_get_object(
        self,
        bucket_name,
        object_name,
        expires=timedelta(days=7),
        response_headers=None,
        request_date=None,
        version_id=None,
        extra_query_params=None,
        change_host=None,
    ):
        """
        Get presigned URL of an object to download its data with expiry time
        and custom request parameters.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param expires: Expiry in seconds; defaults to 7 days.
        :param response_headers: Optional response_headers argument to
                                  specify response fields like date, size,
                                  type of file, data about server, etc.
        :param request_date: Optional request_date argument to
                              specify a different request date. Default is
                              current date.
        :param version_id: Version ID of the object.
        :param extra_query_params: Extra query parameters for advanced usage.
        :param change_host: Change the host for this presign temporaryly.
        This parameter
                            is for the circumstance in which your base url is
                            set with private IP address
                            such as 127.0.0.1 or 0.0.0.0 and you want to
                            create a url with public IP address.
        :return: URL string.

        Example::
            from datetime import timedelta
            from miniopy_async import Minio
            import asyncio

            async def main():
                client = Minio(
                    "play.min.io",
                    access_key="Q3AM3UQ867SPQQA43P2F",
                    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                    secure=True  # http for False, https for True
                )

                # Get presigned URL string to download 'my-object' in
                # 'my-bucket' with default expiry (i.e. 7 days).
                print('example one')
                url = await client.presigned_get_object("my-bucket",
                "my-object")
                print('url:', url)

                # Get presigned URL string to download 'my-object' in
                # 'my-bucket' with two hours expiry.
                print('example two')
                url = await client.presigned_get_object(
                    "my-bucket", "my-object", expires=timedelta(hours=2),
                )
                print('url:', url)

                # Get presigned URL string to download 'my-object' in
                # 'my-bucket' with public IP address when using private IP
                address.
                client = Minio(
                    "127.0.0.1:9000",
                    access_key="your access key",
                    secret_key="you secret key",
                    secure=False  # http for False, https for True
                )

                print('example three')
                url = await client.presigned_get_object(
                    "my-bucket",
                    "my-object",
                    change_host='https://YOURHOST:YOURPORT',
                )
                print('url:', url)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        return await self.get_presigned_url(
            "GET",
            bucket_name,
            object_name,
            expires,
            response_headers=response_headers,
            request_date=request_date,
            version_id=version_id,
            extra_query_params=extra_query_params,
            change_host=change_host,
        )

    async def presigned_put_object(
        self, bucket_name, object_name, expires=timedelta(days=7), change_host=None
    ):
        """
        Get presigned URL of an object to upload data with expiry time and
        custom request parameters.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param expires: Expiry in seconds; defaults to 7 days.
        :param change_host: Change the host for this presign temporaryly.
        This parameter
                            is for the circumstance in which your base url is
                            set with private IP address
                            such as 127.0.0.1 or 0.0.0.0 and you want to
                            create a url with public IP address.
        :return: URL string.

        Example::
            from datetime import timedelta
            from miniopy_async import Minio
            import asyncio

            async def main():
                client = Minio(
                    "play.min.io",
                    access_key="Q3AM3UQ867SPQQA43P2F",
                    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                    secure=True  # http for False, https for True
                )

                # Get presigned URL string to upload data to 'my-object' in
                # 'my-bucket' with default expiry (i.e. 7 days).
                url = await client.presigned_put_object("my-bucket",
                "my-object")
                print('url:', url)

                # Get presigned URL string to upload data to 'my-object' in
                # 'my-bucket' with two hours expiry.
                url = await client.presigned_put_object(
                    "my-bucket", "my-object", expires=timedelta(hours=2),
                )
                print('url:', url)

                # Get presigned URL string to upload data to 'my-object' in
                # 'my-bucket' with public IP address when using private IP
                address.
                client = Minio(
                    "127.0.0.1:9000",
                    access_key="your access key",
                    secret_key="you secret key",
                    secure=False  # http for False, https for True
                )

                print('example three')
                url = await client.presigned_put_object(
                    "my-bucket",
                    "my-object",
                    change_host='https://YOURHOST:YOURPORT',
                )
                print('url:', url)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        return await self.get_presigned_url(
            "PUT", bucket_name, object_name, expires, change_host=change_host
        )

    async def presigned_post_policy(self, policy):
        """
        Get form-data of PostPolicy of an object to upload its data using POST
        method.

        :param policy: :class:`PostPolicy <PostPolicy>`.
        :return: :dict: contains form-data.

        Example::
            from datetime import datetime, timedelta
            from miniopy_async import Minio
            from miniopy_async.datatypes import PostPolicy
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            policy = PostPolicy(
                "my-bucket", datetime.utcnow() + timedelta(days=10),
            )
            policy.add_starts_with_condition("key", "my/object/prefix/")
            policy.add_content_length_range_condition(1*1024*1024, 10*1024*1024)

            async def main():
                form_data = await client.presigned_post_policy(policy)
                curl_cmd = (
                    "curl -X POST "
                    "https://play.min.io/my-bucket "
                    "{0} -F file=@<FILE>"
                ).format(
                    " ".join(["-F {0}={1}".format(k, v) for k,
                    v in form_data.items()]),
                )
                print('curl_cmd:',curl_cmd)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        if not isinstance(policy, PostPolicy):
            raise ValueError("policy must be PostPolicy type")
        if not self._provider:
            raise ValueError(
                "anonymous access does not require presigned post form-data",
            )
        return policy.form_data(
            self._provider.retrieve(),
            await self._get_region(policy.bucket_name, None),
        )

    async def delete_bucket_replication(self, bucket_name):
        """
        Delete replication configuration of a bucket.

        :param bucket_name: Name of the bucket.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.delete_bucket_replication("my-bucket")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        await self._execute("DELETE", bucket_name, query_params={"replication": ""})

    async def get_bucket_replication(self, bucket_name):
        """
        Get bucket replication configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :return: :class:`ReplicationConfig <ReplicationConfig>` object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                config = await client.get_bucket_replication("my-bucket")
                print(config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        try:
            async with aiohttp.ClientSession() as session:
                response = await self._execute(
                    "GET",
                    bucket_name,
                    query_params={"replication": ""},
                    session=session,
                )
                return unmarshal(ReplicationConfig, await response.text())
        except S3Error as exc:
            if exc.code != "ReplicationConfigurationNotFoundError":
                raise
        return None

    async def set_bucket_replication(self, bucket_name, config):
        """
        Set bucket replication configuration to a bucket.

        :param bucket_name: Name of the bucket.
        :param config: :class:`ReplicationConfig <ReplicationConfig>` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.commonconfig import DISABLED, ENABLED, AndOperator, Filter, Tags
            from miniopy_async.replicationconfig import (DeleteMarkerReplication, Destination, ReplicationConfig, Rule)
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            bucket_tags = Tags.new_bucket_tags()
            bucket_tags["Project"] = "Project One"
            bucket_tags["User"] = "jsmith"

            config = ReplicationConfig(
                "REPLACE-WITH-ACTUAL-ROLE",
                [
                    Rule(
                        Destination(
                            "REPLACE-WITH-ACTUAL-DESTINATION-BUCKET-ARN",
                        ),
                        ENABLED,
                        delete_marker_replication=DeleteMarkerReplication(
                            DISABLED,
                        ),
                        rule_filter=Filter(
                            AndOperator(
                                "TaxDocs",
                                bucket_tags,
                            ),
                        ),
                        rule_id="rule1",
                        priority=1,
                    ),
                ],
            )

            async def main():
                await client.set_bucket_replication("my-bucket", config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        if not isinstance(config, ReplicationConfig):
            raise ValueError("config must be ReplicationConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params={"replication": ""},
        )

    async def delete_bucket_lifecycle(self, bucket_name):
        """
        Delete notification configuration of a bucket.

        :param bucket_name: Name of the bucket.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.delete_bucket_lifecycle("my-bucket")

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        await self._execute("DELETE", bucket_name, query_params={"lifecycle": ""})

    async def get_bucket_lifecycle(self, bucket_name):
        """
        Get bucket lifecycle configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :return: :class:`LifecycleConfig <LifecycleConfig>` object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                config = await client.get_bucket_lifecycle("my-bucket")
                print(config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        try:
            async with aiohttp.ClientSession() as session:
                response = await self._execute(
                    "GET", bucket_name, query_params={"lifecycle": ""}, session=session
                )
                return unmarshal(LifecycleConfig, await response.text())
        except S3Error as exc:
            if exc.code != "NoSuchLifecycleConfiguration":
                raise
        return None

    async def set_bucket_lifecycle(self, bucket_name, config):
        """
        Set bucket lifecycle configuration to a bucket.

        :param bucket_name: Name of the bucket.
        :param config: :class:`LifecycleConfig <LifecycleConfig>` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.commonconfig import ENABLED, Filter
            from miniopy_async.lifecycleconfig import Expiration,
            LifecycleConfig, Rule, Transition
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            config = LifecycleConfig(
                [
                    Rule(
                        ENABLED,
                        rule_filter=Filter(prefix="documents/"),
                        rule_id="rule1",
                        transition=Transition(days=30, storage_class="GLACIER"),
                    ),
                    Rule(
                        ENABLED,
                        rule_filter=Filter(prefix="logs/"),
                        rule_id="rule2",
                        expiration=Expiration(days=365),
                    ),
                ],
            )

            async def main():
                await client.set_bucket_lifecycle("my-bucket", config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        if not isinstance(config, LifecycleConfig):
            raise ValueError("config must be LifecycleConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params={"lifecycle": ""},
        )

    async def delete_bucket_tags(self, bucket_name):
        """
        Delete tags configuration of a bucket.

        :param bucket_name: Name of the bucket.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.delete_bucket_tags("my-bucket")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        await self._execute("DELETE", bucket_name, query_params={"tagging": ""})

    async def get_bucket_tags(self, bucket_name):
        """
        Get tags configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :return: :class:`Tags <Tags>` object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                tags = await client.get_bucket_tags("my-bucket")
                print(tags)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        try:
            async with aiohttp.ClientSession() as session:
                response = await self._execute(
                    "GET", bucket_name, query_params={"tagging": ""}, session=session
                )
                tagging = unmarshal(Tagging, await response.text())
                return tagging.tags
        except S3Error as exc:
            if exc.code != "NoSuchTagSet":
                raise
        return None

    async def set_bucket_tags(self, bucket_name, tags):
        """
        Set tags configuration to a bucket.

        :param bucket_name: Name of the bucket.
        :param tags: :class:`Tags <Tags>` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.commonconfig import Tags
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            tags = Tags.new_bucket_tags()
            tags["Project"] = "Project One"
            tags["User"] = "jsmith"

            async def main():
                await client.set_bucket_tags("my-bucket", tags)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        if not isinstance(tags, Tags):
            raise ValueError("tags must be Tags type")
        body = marshal(Tagging(tags))
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params={"tagging": ""},
        )

    async def delete_object_tags(self, bucket_name, object_name, version_id=None):
        """
        Delete tags configuration of an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the Object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.delete_object_tags("my-bucket")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        query_params = {"versionId": version_id} if version_id else {}
        query_params["tagging"] = ""
        await self._execute(
            "DELETE",
            bucket_name,
            object_name=object_name,
            query_params=query_params,
        )

    async def get_object_tags(self, bucket_name, object_name, version_id=None):
        """
        Get tags configuration of a object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the Object.
        :return: :class:`Tags <Tags>` object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                tags = await client.get_object_tags("my-bucket", "my-object")
                print(tags)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        query_params = {"versionId": version_id} if version_id else {}
        query_params["tagging"] = ""
        try:
            async with aiohttp.ClientSession() as session:
                response = await self._execute(
                    "GET",
                    bucket_name,
                    object_name=object_name,
                    query_params=query_params,
                    session=session,
                )
                tagging = unmarshal(Tagging, await response.text())
                return tagging.tags
        except S3Error as exc:
            if exc.code != "NoSuchTagSet":
                raise
        return None

    async def set_object_tags(self, bucket_name, object_name, tags, version_id=None):
        """
        Set tags configuration to an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the Object.
        :param tags: :class:`Tags <Tags>` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.commonconfig import Tags
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            tags = Tags.new_object_tags()
            tags["Project"] = "Project One"
            tags["User"] = "jsmith"

            async def main():
                await client.set_object_tags("my-bucket", "my-object", tags)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        if not isinstance(tags, Tags):
            raise ValueError("tags must be Tags type")
        body = marshal(Tagging(tags))
        query_params = {"versionId": version_id} if version_id else {}
        query_params["tagging"] = ""
        await self._execute(
            "PUT",
            bucket_name,
            object_name=object_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params=query_params,
        )

    async def enable_object_legal_hold(
        self,
        bucket_name,
        object_name,
        version_id=None,
    ):
        """
        Enable legal hold on an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.enable_object_legal_hold("my-bucket", "my-object")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        body = marshal(LegalHold(True))
        query_params = {"versionId", version_id} if version_id else {}
        query_params["legal-hold"] = ""
        await self._execute(
            "PUT",
            bucket_name,
            object_name=object_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params=query_params,
        )

    async def disable_object_legal_hold(
        self,
        bucket_name,
        object_name,
        version_id=None,
    ):
        """
        Disable legal hold on an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.disable_object_legal_hold("my-bucket", "my-object")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        body = marshal(LegalHold(False))
        query_params = {"versionId", version_id} if version_id else {}
        query_params["legal-hold"] = ""
        await self._execute(
            "PUT",
            bucket_name,
            object_name=object_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params=query_params,
        )

    async def is_object_legal_hold_enabled(
        self,
        bucket_name,
        object_name,
        version_id=None,
    ):
        """
        Returns true if legal hold is enabled on an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                if await client.is_object_legal_hold_enabled("my-bucket",
                "my-object"):
                    print("legal hold is enabled on my-object")
                else:
                    print("legal hold is not enabled on my-object")

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        query_params = {"versionId", version_id} if version_id else {}
        query_params["legal-hold"] = ""
        try:
            async with aiohttp.ClientSession() as session:
                response = await self._execute(
                    "GET",
                    bucket_name,
                    object_name=object_name,
                    query_params=query_params,
                    session=session,
                )
                legal_hold = unmarshal(LegalHold, await response.text())
                return legal_hold.status
        except S3Error as exc:
            if exc.code != "NoSuchObjectLockConfiguration":
                raise
        return False

    async def delete_object_lock_config(self, bucket_name):
        """
        Delete object-lock configuration of a bucket.

        :param bucket_name: Name of the bucket.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.delete_object_lock_config("my-bucket")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        await self.set_object_lock_config(
            bucket_name, ObjectLockConfig(None, None, None)
        )

    async def get_object_lock_config(self, bucket_name):
        """
        Get object-lock configuration of a bucket.

        :param bucket_name: Name of the bucket.
        :return: :class:`ObjectLockConfig <ObjectLockConfig>` object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                config = await client.get_object_lock_config("my-bucket")
                print(config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "GET", bucket_name, query_params={"object-lock": ""}, session=session
            )
            return unmarshal(ObjectLockConfig, await response.text())

    async def set_object_lock_config(self, bucket_name, config):
        """
        Set object-lock configuration to a bucket.

        :param bucket_name: Name of the bucket.
        :param config: :class:`ObjectLockConfig <ObjectLockConfig>` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.commonconfig import GOVERNANCE
            from miniopy_async.objectlockconfig import DAYS, ObjectLockConfig
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            config = ObjectLockConfig(GOVERNANCE, 15, DAYS)

            async def main():
                await client.set_object_lock_config("my-bucket", config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        if not isinstance(config, ObjectLockConfig):
            raise ValueError("config must be ObjectLockConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params={"object-lock": ""},
        )

    async def get_object_retention(
        self,
        bucket_name,
        object_name,
        version_id=None,
    ):
        """
        Get retention configuration of an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the object.
        :return: :class:`Retention <Retention>` object.

        Example::
            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                config = await client.get_object_retention("my-bucket",
                "my-object")
                print(config)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        query_params = {"versionId", version_id} if version_id else {}
        query_params["retention"] = ""
        try:
            async with aiohttp.ClientSession() as session:
                response = await self._execute(
                    "GET",
                    bucket_name,
                    object_name=object_name,
                    query_params=query_params,
                    session=session,
                )
                return unmarshal(Retention, await response.text())
        except S3Error as exc:
            if exc.code != "NoSuchObjectLockConfiguration":
                raise
        return None

    async def set_object_retention(
        self,
        bucket_name,
        object_name,
        config,
        version_id=None,
    ):
        """
        Set retention configuration on an object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param version_id: Version ID of the object.
        :param config: :class:`Retention <Retention>` object.

        Example::
            from datetime import datetime, timedelta
            from miniopy_async import Minio
            from miniopy_async.commonconfig import GOVERNANCE
            from miniopy_async.retention import Retention
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            config = Retention(GOVERNANCE, datetime.utcnow() + timedelta(
            days=10))

            async def main():
                await client.set_object_retention(
                    "my-bucket",
                    "my-object",
                    config
                )

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name)
        check_non_empty_string(object_name)
        if not isinstance(config, Retention):
            raise ValueError("config must be Retention type")
        body = marshal(config)
        query_params = {"versionId", version_id} if version_id else {}
        query_params["retention"] = ""
        await self._execute(
            "PUT",
            bucket_name,
            object_name=object_name,
            body=body,
            headers={"Content-MD5": md5sum_hash(body)},
            query_params=query_params,
        )

    async def upload_snowball_objects(
        self,
        bucket_name,
        object_list,
        metadata=None,
        sse=None,
        tags=None,
        retention=None,
        legal_hold=False,
        staging_filename=None,
        compression=False,
    ):
        """
        Uploads multiple objects in a single put call. It is done by creating
        intermediate TAR file optionally compressed which is uploaded to S3
        service.

        :param bucket_name: Name of the bucket.
        :param object_list: An iterable containing
            :class:`SnowballObject <SnowballObject>` object.
        :param metadata: Any additional metadata to be uploaded along
            with your PUT request.
        :param sse: Server-side encryption.
        :param tags: :class:`Tags` for the object.
        :param retention: :class:`Retention` configuration object.
        :param legal_hold: Flag to set legal hold for the object.
        :param staging_filename: A staging filename to create intermediate tarball.
        :param compression: Flag to compress TAR ball.
        :return: :class:`ObjectWriteResult` object.

        Example::
            from miniopy_async import Minio
            from miniopy_async.commonconfig import SnowballObject
            import io
            from datetime import datetime
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True,  # http for False, https for True
            )

            async def main():
                result = await client.upload_snowball_objects(
                    "my-bucket",
                    [
                        SnowballObject("my-object1", filename="filename"),
                        SnowballObject(
                            "my-object2", data=io.BytesIO(b"hello"), length=5,
                        ),
                        SnowballObject(
                            "my-object3", data=io.BytesIO(b"world"), length=5,
                            mod_time=datetime.now(),
                        ),
                    ],
                )

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
            loop.close()
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)

        object_name = f"snowball.{random()}.tar"

        # turn list like objects into an iterator.
        object_list = itertools.chain(object_list)

        metadata = metadata or {}
        metadata["X-Amz-Meta-Snowball-Auto-Extract"] = "true"

        name = staging_filename
        mode = "w:gz" if compression else "w"
        fileobj = None if name else BytesIO()
        with tarfile.open(name=name, mode=mode, fileobj=fileobj) as tar:
            for obj in object_list:
                if obj.filename:
                    tar.add(obj.filename, obj.object_name)
                else:
                    info = tarfile.TarInfo(obj.object_name)
                    info.size = obj.length
                    info.mtime = int(
                        time.to_float(obj.mod_time or time.utcnow()),
                    )
                    tar.addfile(info, obj.data)

        if not name:
            length = fileobj.tell()
            fileobj.seek(0)
        else:
            length = os.stat(name).st_size

        part_size = 0 if length < MIN_PART_SIZE else length

        if name:
            return await self.fput_object(
                bucket_name,
                object_name,
                staging_filename,
                metadata=metadata,
                sse=sse,
                tags=tags,
                retention=retention,
                legal_hold=legal_hold,
                part_size=part_size,
            )
        return await self.put_object(
            bucket_name,
            object_name,
            fileobj,
            length,
            metadata=metadata,
            sse=sse,
            tags=tags,
            retention=retention,
            legal_hold=legal_hold,
            part_size=part_size,
        )

    async def _list_objects(
        # pylint: disable=too-many-arguments,too-many-branches
        self,
        bucket_name,
        continuation_token=None,
        # listV2 only
        delimiter=None,
        # all
        encoding_type=None,
        # all
        fetch_owner=None,
        # listV2 only
        include_user_meta=None,
        # MinIO specific listV2.
        max_keys=None,
        # all
        prefix=None,
        # all
        start_after=None,
        # all: v1:marker, versioned:key_marker
        version_id_marker=None,
        # versioned
        use_api_v1=False,
        include_version=False,
    ):
        """
        List objects optionally including versions.
        Note: Its required to send empty values to delimiter/prefix and 1000 to
        max-keys when not provided for server-side bucket policy evaluation to
        succeed; otherwise AccessDenied error will be returned for such
        policies.
        """

        check_bucket_name(bucket_name)

        if version_id_marker:
            include_version = True

        is_truncated = True

        while is_truncated:
            query = {}
            if include_version:
                query["versions"] = ""
            elif not use_api_v1:
                query["list-type"] = "2"

            if not include_version and not use_api_v1:
                if continuation_token:
                    query["continuation-token"] = continuation_token
                if fetch_owner:
                    query["fetch-owner"] = "true"
                if include_user_meta:
                    query["metadata"] = "true"
            query["delimiter"] = delimiter or ""
            if encoding_type:
                query["encoding-type"] = encoding_type
            query["max-keys"] = str(max_keys or 1000)
            query["prefix"] = prefix or ""
            if start_after:
                if include_version:
                    query["key-marker"] = start_after
                elif use_api_v1:
                    query["marker"] = start_after
                else:
                    query["start-after"] = start_after
            if version_id_marker:
                query["version-id-marker"] = version_id_marker

            async with aiohttp.ClientSession() as session:
                response = await self._execute(
                    "GET", bucket_name, query_params=query, session=session
                )

                (
                    objects,
                    is_truncated,
                    start_after,
                    version_id_marker,
                ) = await parse_list_objects(response)

                yield objects

            if not include_version:
                version_id_marker = None
                if not use_api_v1:
                    continuation_token = start_after

    async def _list_multipart_uploads(
        self,
        bucket_name,
        delimiter=None,
        encoding_type=None,
        key_marker=None,
        max_uploads=None,
        prefix=None,
        upload_id_marker=None,
        extra_headers=None,
        extra_query_params=None,
    ):
        """
        Execute ListMultipartUploads S3 API.

        :param bucket_name: Name of the bucket.
        :param delimiter: (Optional) Delimiter on listing.
        :param encoding_type: (Optional) Encoding type.
        :param key_marker: (Optional) Key marker.
        :param max_uploads: (Optional) Maximum upload information to fetch.
        :param prefix: (Optional) Prefix on listing.
        :param upload_id_marker: (Optional) Upload ID marker.
        :param extra_headers: (Optional) Extra headers for advanced usage.
        :param extra_query_params: (Optional) Extra query parameters for
            advanced usage.
        :return:
            :class:`ListMultipartUploadsResult <ListMultipartUploadsResult>`
                object
        """

        query_params = extra_query_params or {}
        query_params.update(
            {
                "uploads": "",
                "delimiter": delimiter or "",
                "max-uploads": str(max_uploads or 1000),
                "prefix": prefix or "",
                "encoding-type": "url",
            },
        )
        if encoding_type:
            query_params["encoding-type"] = encoding_type
        if key_marker:
            query_params["key-marker"] = key_marker
        if upload_id_marker:
            query_params["upload-id-marker"] = upload_id_marker

        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "GET",
                bucket_name,
                query_params=query_params,
                headers=extra_headers,
                session=session,
            )
            return await ListMultipartUploadsResult.from_async_response(response.text())

    async def _list_parts(
        self,
        bucket_name,
        object_name,
        upload_id,
        max_parts=None,
        part_number_marker=None,
        extra_headers=None,
        extra_query_params=None,
    ):
        """
        Execute ListParts S3 API.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param upload_id: Upload ID.
        :param max_parts: (Optional) Maximum parts information to fetch.
        :param part_number_marker: (Optional) Part number marker.
        :param extra_headers: (Optional) Extra headers for advanced usage.
        :param extra_query_params: (Optional) Extra query parameters for
            advanced usage.
        :return: :class:`ListPartsResult <ListPartsResult>` object
        """

        query_params = extra_query_params or {}
        query_params.update(
            {
                "uploadId": upload_id,
                "max-parts": str(max_parts or 1000),
            },
        )
        if part_number_marker:
            query_params["part-number-marker"] = part_number_marker

        async with aiohttp.ClientSession() as session:
            response = await self._execute(
                "GET",
                bucket_name,
                object_name=object_name,
                query_params=query_params,
                headers=extra_headers,
                session=session,
            )
            return await ListPartsResult.from_async_response(response.text())
