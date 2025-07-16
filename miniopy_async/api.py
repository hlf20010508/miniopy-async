# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage, (C)
# 2015, 2016, 2017 MinIO, Inc.
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

# pylint: disable=too-many-lines,disable=too-many-branches,too-many-statements
# pylint: disable=too-many-arguments

"""Simple Storage Service (aka S3) client to perform bucket and object operations."""

from __future__ import absolute_import, annotations

import asyncio
import itertools
import json
import os
import ssl
import tarfile
from collections.abc import Iterable
from datetime import datetime, timedelta
from io import BytesIO
from random import random
from typing import Any, AsyncGenerator, BinaryIO, TextIO, cast
from urllib.parse import urlunsplit
from xml.etree import ElementTree as ET

import certifi
from aiohttp import ClientResponse, ClientSession, ClientTimeout, TCPConnector
from aiohttp.typedefs import LooseHeaders
from aiohttp_retry import ExponentialRetry, RetryClient
from multidict import CIMultiDict

from . import time
from .commonconfig import COPY, REPLACE, ComposeSource, CopySource, SnowballObject, Tags
from .credentials import Credentials, StaticProvider
from .credentials.providers import Provider
from .datatypes import (
    AsyncEventIterable,
    Bucket,
    CompleteMultipartUploadResult,
    DeleteErrors,
    ListAllMyBucketsResult,
    ListMultipartUploadsResult,
    ListObjects,
    ListPartsResult,
    Object,
    Part,
    PostPolicy,
    parse_copy_object,
    parse_list_objects,
)
from .deleteobjects import DeleteError, DeleteObject, DeleteRequest, DeleteResult
from .error import InvalidResponseError, S3Error, ServerError
from .helpers import (
    _DEFAULT_USER_AGENT,
    MAX_MULTIPART_COUNT,
    MAX_MULTIPART_OBJECT_SIZE,
    MAX_PART_SIZE,
    MIN_PART_SIZE,
    BaseURL,
    DictType,
    ObjectWriteResult,
    ProgressType,
    Substream,
    check_bucket_name,
    check_object_name,
    check_sse,
    check_ssec,
    genheaders,
    get_part_info,
    headers_to_strings,
    is_valid_policy_type,
    makedirs,
    md5sum_hash,
    queryencode,
    sha256_hash,
)
from .legalhold import LegalHold
from .lifecycleconfig import LifecycleConfig
from .notificationconfig import NotificationConfig
from .objectlockconfig import ObjectLockConfig
from .replicationconfig import ReplicationConfig
from .retention import Retention
from .select import SelectObjectReader, SelectRequest
from .signer import presign_v4, sign_v4_s3
from .sse import Sse, SseCustomerKey
from .sseconfig import SSEConfig
from .tagging import Tagging
from .versioningconfig import VersioningConfig
from .xml import Element, SubElement, findtext, getbytes, marshal, unmarshal


class Minio:  # pylint: disable=too-many-public-methods
    """
    Simple Storage Service (aka S3) client to perform bucket and object
    operations.

    :param str endpoint: Hostname of a S3 service.
    :param str | None access_key: Access key (aka user ID) of your account in S3 service.
    :param str | None secret_key: Secret Key (aka password) of your account in S3 service.
    :param str | None session_token: Session token of your account in S3 service.
    :param bool secure: Flag to indicate to use secure (TLS) connection to S3service or not.
    :param str | None region: Region name of buckets in S3 service.
    :param Provider | None credentials: Credentials provider of your account in S3 service.
    :param aiohttp.ClientSession | aiohttp_retry.RetryClient | None session: Custom HTTP client session.
    :param bool cert_check: Flag to indicate to verify SSL certificate or not.
    :param str | None server_url: Server url of minio service, used for presigned url.
    :return: :class:`Minio` object
    :rtype: Minio

    .. code-block:: python

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
    """

    _region_map: dict[str, str]
    _base_url: BaseURL
    _user_agent: str
    _trace_stream: TextIO | None
    _provider: Provider | None

    def __init__(
        self,
        endpoint: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        session_token: str | None = None,
        secure: bool = True,
        region: str | None = None,
        session: ClientSession | RetryClient | None = None,
        credentials: Provider | None = None,
        cert_check: bool = True,
        server_url: str | None = None,
    ):
        self._region_map = dict()
        self._base_url = BaseURL(
            ("https://" if secure else "http://") + endpoint,
            region,
        )
        self._server_url = (
            BaseURL(
                server_url,
                region,
            )
            if server_url
            else None
        )
        self._user_agent = _DEFAULT_USER_AGENT
        self._trace_stream = None
        if access_key:
            if secret_key is None:
                raise ValueError("secret key must be provided with access key")
            credentials = StaticProvider(access_key, secret_key, session_token)
        self._provider = credentials
        self._session = session
        self._cert_check = cert_check

    def _ensure_session(self):
        if self._session is None:
            if self._cert_check:
                ssl_context = ssl.create_default_context(
                    cafile=os.environ.get("SSL_CERT_FILE") or certifi.where()
                )
            else:
                ssl_context = ssl.create_default_context(
                    cafile=os.environ.get("SSL_CERT_FILE") or certifi.where()
                )
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            timeout = timedelta(minutes=5).seconds
            client_timeout = ClientTimeout(connect=timeout, sock_read=timeout)

            retry_options = ExponentialRetry(
                attempts=5, factor=0.2, statuses={500, 502, 503, 504}
            )

            self._session = RetryClient(
                ClientSession(
                    connector=TCPConnector(limit=10, ssl=ssl_context),
                    timeout=client_timeout,
                ),
                retry_options=retry_options,
            )

    def set_session(self, session: ClientSession | RetryClient):
        """
        Set custom HTTP client session.

        :param ClientSession | RetryClient session: Custom HTTP client session.
        """
        if not isinstance(session, (ClientSession, RetryClient)):
            raise ValueError("session must be ClientSession or RetryClient type")
        self._session = session

    async def close_session(self):
        """
        Close the HTTP client session.
        """
        if self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()

    def _handle_redirect_response(
        self,
        method: str,
        bucket_name: str | None,
        response: ClientResponse,
        retry: bool = False,
    ) -> tuple[str | None, str | None]:
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

    async def _build_headers(
        self,
        host: str,
        headers: LooseHeaders | DictType | None,
        body: bytes | BytesIO | Substream | None,
        creds: Credentials | None,
    ) -> tuple[dict[str, str], datetime]:
        """Build headers with given parameters."""
        headers = cast(dict[str, str], dict(headers) if headers is not None else {})
        md5sum_added = headers.get("Content-MD5")
        headers["Host"] = host
        headers["User-Agent"] = self._user_agent
        sha256 = None
        md5sum = None

        if body:
            if isinstance(body, BytesIO):
                headers["Content-Length"] = str(body.getbuffer().nbytes)
            elif isinstance(body, Substream):
                headers["Content-Length"] = str(body.size)
            else:
                headers["Content-Length"] = str(len(body))
        if creds:
            if self._base_url.is_https:
                sha256 = "UNSIGNED-PAYLOAD"
                md5sum = None if md5sum_added else md5sum_hash(body)
            else:
                sha256 = await asyncio.to_thread(sha256_hash, body)
        else:
            md5sum = None if md5sum_added else md5sum_hash(body)
        if md5sum:
            headers["Content-MD5"] = md5sum
        if sha256:
            headers["x-amz-content-sha256"] = sha256
        if creds and creds.session_token:
            headers["X-Amz-Security-Token"] = creds.session_token
        date = time.utcnow()
        headers["x-amz-date"] = time.to_amz_date(date)
        return headers, date

    async def _url_open(
        self,
        method: str,
        region: str,
        bucket_name: str | None = None,
        object_name: str | None = None,
        body: bytes | BytesIO | Substream | None = None,
        headers: LooseHeaders | DictType | None = None,
        query_params: DictType | None = None,
        no_body_trace: bool = False,
    ) -> ClientResponse:
        """Execute HTTP request."""
        creds = await self._provider.retrieve() if self._provider else None
        url = self._base_url.build(
            method,
            region,
            bucket_name=bucket_name,
            object_name=object_name,
            query_params=query_params,
        )
        headers, date = await self._build_headers(url.netloc, headers, body, creds)
        if creds:
            headers = sign_v4_s3(
                method,
                url,
                region,
                headers,
                creds,
                cast(str, headers.get("x-amz-content-sha256")),
                date,
            )

        headers = dict(headers)
        if self._trace_stream:
            self._trace_stream.write("---------START-HTTP---------\n")
            query = ("?" + url.query) if url.query else ""
            self._trace_stream.write(f"{method} {url.path}{query} HTTP/1.1\n")
            self._trace_stream.write(
                headers_to_strings(headers, titled_key=True),
            )
            self._trace_stream.write("\n")
            if not no_body_trace and body is not None:
                self._trace_stream.write("\n")
                self._trace_stream.write(
                    body.decode() if isinstance(body, bytes) else str(body),
                )
                self._trace_stream.write("\n")
            self._trace_stream.write("\n")

        http_headers = CIMultiDict()
        for key, value in (headers or {}).items():
            if isinstance(value, (list, tuple)):
                for val in value:
                    http_headers.add(key, val)
            else:
                http_headers.add(key, value)

        self._ensure_session()
        session = cast(ClientSession | RetryClient, self._session)

        response = await session.request(
            method,
            urlunsplit(url),
            data=body,
            headers=http_headers,
        )

        if self._trace_stream:
            self._trace_stream.write(f"HTTP/1.1 {response.status}\n")
            self._trace_stream.write(
                headers_to_strings(response.headers),
            )
            self._trace_stream.write("\n")

        if response.status in [200, 204, 206]:
            if self._trace_stream:
                self._trace_stream.write("\n")
                self._trace_stream.write(await response.text())
                self._trace_stream.write("\n")
                self._trace_stream.write("----------END-HTTP----------\n")
            return response

        response_data = await response.content.read()

        if self._trace_stream and method != "HEAD" and response_data:
            self._trace_stream.write(response_data.decode())
            self._trace_stream.write("\n")

        if method != "HEAD" and "application/xml" not in response.headers.get(
            "content-type",
            "",
        ).split(";"):
            if self._trace_stream:
                self._trace_stream.write("----------END-HTTP----------\n")
            if response.status == 304 and not response_data:
                raise ServerError(
                    f"server failed with HTTP status code {response.status}",
                    response.status,
                )
            raise InvalidResponseError(
                response.status,
                cast(str, response.headers.get("content-type")),
                response_data.decode() if response_data else None,
            )

        if not response_data and method != "HEAD":
            if self._trace_stream:
                self._trace_stream.write("----------END-HTTP----------\n")
            raise InvalidResponseError(
                response.status,
                response.headers.get("content-type"),
                None,
            )

        response_error = (
            S3Error.fromxml(response, response_data.decode()) if response_data else None
        )

        if self._trace_stream:
            self._trace_stream.write("----------END-HTTP----------\n")

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
            if bucket_name is not None:
                self._region_map.pop(bucket_name, None)

        raise response_error

    async def _execute(
        self,
        method: str,
        bucket_name: str | None = None,
        object_name: str | None = None,
        body: bytes | BytesIO | Substream | None = None,
        headers: DictType | None = None,
        query_params: DictType | None = None,
        no_body_trace: bool = False,
    ) -> ClientResponse:
        """Execute HTTP request."""
        region = await self._get_region(bucket_name)

        try:
            response = await self._url_open(
                method,
                region,
                bucket_name=bucket_name,
                object_name=object_name,
                body=body,
                headers=headers,
                query_params=query_params,
                no_body_trace=no_body_trace,
            )
            return response

        except S3Error as exc:
            if exc.code != "RetryHead":
                raise

        # Retry only once on RetryHead error.
        try:
            response = await self._url_open(
                method,
                region,
                bucket_name=bucket_name,
                object_name=object_name,
                body=body,
                headers=headers,
                query_params=query_params,
                no_body_trace=no_body_trace,
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
            raise exc.copy(cast(str, code), cast(str, message))

    async def _get_region(self, bucket_name: str | None) -> str:
        """
        Return region of given bucket either from region cache or set in
        constructor.
        """

        if self._base_url.region:
            return self._base_url.region

        if not bucket_name or not self._provider:
            return "us-east-1"

        region = self._region_map.get(bucket_name)
        if region:
            return region

        # Execute GetBucketLocation REST API to get region of the bucket.
        response = await self._url_open(
            "GET",
            "us-east-1",
            bucket_name=bucket_name,
            query_params={"location": ""},
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

    def set_app_info(self, app_name: str, app_version: str):
        """
        Set your application name and version to user agent header.

        :param str app_name: Application name.
        :param str app_version: Application version.
        :raise ValueError: If application name or version is empty.

        .. code-block:: python

            client.set_app_info('my_app', '1.0.2')
        """
        if not (app_name and app_version):
            raise ValueError("Application name/version cannot be empty.")
        self._user_agent = f"{_DEFAULT_USER_AGENT} {app_name}/{app_version}"

    def trace_on(self, stream: TextIO):
        """
        Enable http trace.

        :param TextIO stream: Stream for writing HTTP call tracing.
        """
        if not stream:
            raise ValueError("Input stream for trace output is invalid.")
        # Save new output stream.
        self._trace_stream = stream

    def trace_off(self):
        """
        Disable HTTP trace.
        """
        self._trace_stream = None

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

    async def select_object_content(
        self,
        bucket_name: str,
        object_name: str,
        request: SelectRequest,
    ) -> SelectObjectReader:
        """
        Select content of an object by SQL expression.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param SelectRequest request: :class:`SelectRequest` object.
        :return: A reader contains requested records and progress information.
        :rtype: SelectObjectReader
        :raise ValueError: If request is not of type :class:`SelectRequest`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        if not isinstance(request, SelectRequest):
            raise ValueError("request must be SelectRequest type")
        body = marshal(request)
        response = await self._execute(
            "POST",
            bucket_name=bucket_name,
            object_name=object_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params={"select": "", "select-type": "2"},
        )
        return SelectObjectReader(response)

    async def make_bucket(
        self,
        bucket_name: str,
        location: str | None = None,
        object_lock: bool = False,
    ):
        """
        Create a bucket with region and object lock.

        :param str bucket_name: Name of the bucket.
        :param str | None location: Region in which the bucket will be created.
        :param bool object_lock: Flag to set object-lock feature.
        :raise ValueError: If location is not same as region passed via base url

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, True, s3_check=self._base_url.is_aws_host)
        if self._base_url.region:
            # Error out if region does not match with region passed via
            # constructor.
            if location and self._base_url.region != location:
                raise ValueError(
                    f"region must be {self._base_url.region}, "
                    f"but {location} was passed"
                )
        location = self._base_url.region or location or "us-east-1"
        headers: DictType | None = (
            {"x-amz-bucket-object-lock-enabled": "true"} if object_lock else None
        )

        body = None
        if location != "us-east-1":
            element = Element("CreateBucketConfiguration")
            SubElement(element, "LocationConstraint", location)
            body = getbytes(element)
        await self._url_open(
            "PUT",
            location,
            bucket_name=bucket_name,
            body=body,
            headers=headers,
        )
        self._region_map[bucket_name] = location

    async def list_buckets(self) -> list[Bucket]:
        """
        List information of all accessible buckets.

        :return: List of :class:`Bucket` object.
        :rtype: list[Bucket]

        .. code-block:: python

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

            asyncio.run(main())
        """
        response = await self._execute("GET")
        result = unmarshal(ListAllMyBucketsResult, await response.text())
        return result.buckets

    async def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a bucket exists.

        :param str bucket_name: Name of the bucket.
        :return: True if the bucket exists.
        :rtype: bool
        :raise ValueError: If bucket not found.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        try:
            await self._execute("HEAD", bucket_name)
            return True
        except S3Error as exc:
            if exc.code != "NoSuchBucket":
                raise
        return False

    async def remove_bucket(self, bucket_name: str):
        """
        Remove an empty bucket.

        :param str bucket_name: Name of the bucket.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        await self._execute("DELETE", bucket_name)
        self._region_map.pop(bucket_name, None)

    async def get_bucket_policy(self, bucket_name: str) -> str:
        """
        Get bucket policy configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :return: Bucket policy configuration as JSON string.
        :rtype: str

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        response = await self._execute("GET", bucket_name, query_params={"policy": ""})
        return await response.text()

    async def delete_bucket_policy(self, bucket_name: str):
        """
        Delete bucket policy configuration of a bucket.

        :param str bucket_name: Name of the bucket.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        await self._execute("DELETE", bucket_name, query_params={"policy": ""})

    async def set_bucket_policy(self, bucket_name: str, policy: str | bytes):
        """
        Set bucket policy configuration to a bucket.

        :param str bucket_name: Name of the bucket.
        :param str | bytes policy: Bucket policy configuration as JSON string.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        is_valid_policy_type(policy)
        await self._execute(
            "PUT",
            bucket_name,
            body=policy if isinstance(policy, bytes) else policy.encode(),
            headers={"Content-MD5": cast(str, md5sum_hash(policy))},
            query_params={"policy": ""},
        )

    async def get_bucket_notification(self, bucket_name: str) -> NotificationConfig:
        """
        Get notification configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :return: :class:`NotificationConfig` object.
        :rtype: NotificationConfig

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        response = await self._execute(
            "GET", bucket_name, query_params={"notification": ""}
        )
        return unmarshal(NotificationConfig, await response.text())

    async def set_bucket_notification(
        self, bucket_name: str, config: NotificationConfig
    ):
        """
        Set notification configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :param NotificationConfig config: class:`NotificationConfig` object.
        :raise ValueError: If config is not of type :class:`NotificationConfig`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        if not isinstance(config, NotificationConfig):
            raise ValueError("config must be NotificationConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params={"notification": ""},
        )

    async def delete_bucket_notification(self, bucket_name: str):
        """
        Delete notification configuration of a bucket. On success, S3 service
        stops notification of events previously set of the bucket.

        :param str bucket_name: Name of the bucket.

        .. code-block:: python

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

            asyncio.run(main())
        """
        await self.set_bucket_notification(bucket_name, NotificationConfig())

    async def set_bucket_encryption(self, bucket_name: str, config: SSEConfig):
        """
        Set encryption configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :param SSEConfig config: :class:`SSEConfig` object.
        :raise ValueError: If config is not of type :class:`SSEConfig`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        if not isinstance(config, SSEConfig):
            raise ValueError("config must be SSEConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params={"encryption": ""},
        )

    async def get_bucket_encryption(self, bucket_name: str) -> SSEConfig | None:
        """
        Get encryption configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :return: :class:`SSEConfig` object.
        :rtype: SSEConfig | None
        :raise S3Error: If server side encryption configuration is not found.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        try:
            response = await self._execute(
                "GET", bucket_name, query_params={"encryption": ""}
            )
            return unmarshal(SSEConfig, await response.text())
        except S3Error as exc:
            if exc.code != "ServerSideEncryptionConfigurationNotFoundError":
                raise
        return None

    async def delete_bucket_encryption(self, bucket_name: str):
        """
        Delete encryption configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :raise S3Error: If server side encryption configuration is not found.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
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
        bucket_name: str,
        prefix: str = "",
        suffix: str = "",
        events: tuple[str, ...] = (
            "s3:ObjectCreated:*",
            "s3:ObjectRemoved:*",
            "s3:ObjectAccessed:*",
        ),
    ) -> AsyncEventIterable:
        """
        Listen events of object prefix and suffix of a bucket. Caller should
        iterate returned iterator to read new events.

        :param str bucket_name: Name of the bucket.
        :param str prefix: Listen events of object starts with prefix.
        :param str suffix: Listen events of object ends with suffix.
        :param tuple[str, ...] events: Events to listen.
        :return: Iterator of event records as dict.
        :rtype: AsyncEventIterable[aiohttp.ClientResponse]
        :raise ValueError: If ListenBucketNotification API is not supported in Amazon S3.

        .. code-block:: python

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
                    events=("s3:ObjectCreated:*", "s3:ObjectRemoved:*"),
                )
                async for event in events:
                    print('event:',event)

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
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
                    "events": cast(tuple[str], events),
                },
            ),
        )

    async def set_bucket_versioning(
        self,
        bucket_name: str,
        config: VersioningConfig,
    ):
        """
        Set versioning configuration to a bucket.

        :param str bucket_name: Name of the bucket.
        :param VersioningConfig config: :class:`VersioningConfig`.
        :raise ValueError: If config is not of type :class:`VersioningConfig`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        if not isinstance(config, VersioningConfig):
            raise ValueError("config must be VersioningConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params={"versioning": ""},
        )

    async def get_bucket_versioning(self, bucket_name: str) -> VersioningConfig:
        """
        Get versioning configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :return: :class:`VersioningConfig`.
        :rtype: VersioningConfig

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        response = await self._execute(
            "GET", bucket_name, query_params={"versioning": ""}
        )
        return unmarshal(VersioningConfig, await response.text())

    async def fput_object(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
        metadata: DictType | None = None,
        sse: Sse | None = None,
        progress: ProgressType | None = None,
        part_size: int = 0,
        num_parallel_uploads: int = 3,
        tags: Tags | None = None,
        retention: Retention | None = None,
        legal_hold: bool = False,
    ) -> ObjectWriteResult:
        """
        Uploads data from a file to an object in a bucket.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str file_path: Name of file to upload.
        :param str content_type: Content type of the object.
        :param DictType | None metadata: Any additional metadata to be uploaded along
            with your PUT request.
        :param Sse | None sse: Server-side encryption.
        :param ProgressType | None progress: A progress object.
        :param int part_size: Multipart part size
        :param int num_parallel_uploads: Number of parallel uploads.
        :param Tags | None tags: :class:`Tags` for the object.
        :param Retention | None retention: :class:`Retention` configuration object.
        :param bool legal_hold: Flag to set legal hold for the object.
        :return: :class:`ObjectWriteResult` object.
        :rtype: ObjectWriteResult

        .. code-block:: python

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

            asyncio.run(main())
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
        bucket_name: str,
        object_name: str,
        file_path: str,
        request_headers: DictType | None = None,
        ssec: SseCustomerKey | None = None,
        version_id: str | None = None,
        extra_query_params: DictType | None = None,
        tmp_file_path: str | None = None,
        progress: ProgressType | None = None,
    ) -> Object:
        """
        Downloads data of an object to file.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str file_path: Name of file to download.
        :param DictType | None request_headers: Any additional headers to be added with GET request.
        :param SseCustomerKey | None ssec: Server-side encryption customer key.
        :param str | None version_id: Version-ID of the object.
        :param DictType | None extra_query_params: Extra query parameters for advanced usage.
        :param str | None tmp_file_path: Path to a temporary file.
        :param ProgressType | None progress: A progress object.
        :return: Object information.
        :rtype: Object
        :raise ValueError: If file_path is a directory.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)

        if os.path.isdir(file_path):
            raise ValueError(f"file {file_path} is a directory")

        # Create top level directory if needed.
        makedirs(os.path.dirname(file_path))

        stat = await self.stat_object(
            bucket_name,
            object_name,
            ssec,
            version_id=version_id,
            extra_headers=request_headers,
        )

        etag = queryencode(cast(str, stat.etag))
        # Write to a temporary file "file_path.part.minio" before saving.
        tmp_file_path = tmp_file_path or f"{file_path}.{etag}.part.minio"

        try:

            async def write_to_file():
                response = await self.get_object(
                    bucket_name,
                    object_name,
                    request_headers=request_headers,
                    ssec=ssec,
                    version_id=version_id,
                    extra_query_params=extra_query_params,
                )

                if progress:
                    # Set progress bar length and object name before upload
                    length = int(response.headers.get("content-length", 0))
                    await progress.set_meta(
                        object_name=object_name, total_length=length
                    )

                with open(tmp_file_path, "wb") as tmp_file:
                    async for data in response.content.iter_chunked(n=1024 * 1024):
                        size = tmp_file.write(data)
                        if progress:
                            await progress.update(size)

            await write_to_file()

            if os.path.exists(file_path):
                os.remove(file_path)  # For windows compatibility.
            os.rename(tmp_file_path, file_path)

            return stat
        finally:
            pass

    async def get_object(
        self,
        bucket_name: str,
        object_name: str,
        offset: int = 0,
        length: int = 0,
        request_headers: DictType | None = None,
        ssec: SseCustomerKey | None = None,
        version_id: str | None = None,
        extra_query_params: DictType | None = None,
    ) -> ClientResponse:
        """
        Get data of an object. Returned response should be closed after use to
        release network resources. To reuse the connection, it's required to
        call `response.release()` explicitly.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param int offset: Start byte position of object data.
        :param int length: Number of bytes of object data from offset.
        :param DictType | None request_headers: Any additional headers to be added with GET
                                request.
        :param SseCustomerKey | None ssec: Server-side encryption customer key.
        :param str | None version_id: Version-ID of the object.
        :param DictType | None extra_query_params: Extra query parameters for advanced usage.
        :return: :class:`aiohttp.client_reqrep.ClientResponse` object.
        :rtype: aiohttp.ClientResponse

        .. code-block:: python

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
                print("example one")
                _response = await client.get_object("my-bucket", "my-object")
                # Read data from response.

                # Get data of an object from offset and length.
                print("example two")
                _response = await client.get_object(
                    "my-bucket",
                    "my-object",
                    offset=512,
                    length=1024,
                )
                # Read data from response.

                # Get data of an object of version-ID.
                print("example three")
                _response = await client.get_object(
                    "my-bucket",
                    "my-object",
                    version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
                )
                # Read data from response.

                # Get data of an SSE-C encrypted object.
                print("example four")
                _response = await client.get_object(
                    "my-bucket",
                    "my-object",
                    ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
                )
                # Read data from response.

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        check_ssec(ssec)

        headers = cast(DictType, ssec.headers() if ssec else {})
        headers.update(request_headers or {})

        if offset or length:
            end = (offset + length - 1) if length else ""
            headers["Range"] = f"bytes={offset}-{end}"

        if version_id:
            extra_query_params = extra_query_params or {}
            extra_query_params["versionId"] = version_id

        return await self._execute(
            "GET",
            bucket_name,
            object_name,
            headers=headers,
            query_params=extra_query_params,
        )

    async def prompt_object(
        self,
        bucket_name: str,
        object_name: str,
        prompt: str,
        lambda_arn: str | None = None,
        request_headers: DictType | None = None,
        ssec: SseCustomerKey | None = None,
        version_id: str | None = None,
        **kwargs: Any | None,
    ) -> ClientResponse:
        """
        Prompt an object using natural language.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str prompt: Prompt the Object to interact with the AI model.
                                request.
        :param str | None lambda_arn: Lambda ARN to use for prompt.
        :param DictType | None request_headers: Any additional headers to be added with POST
        :param SseCustomerKey | None ssec: Server-side encryption customer key.
        :param str | None version_id: Version-ID of the object.
        :param Any | None kwargs: Extra parameters for advanced usage.
        :return: :class:`aiohttp.ClientResponse` object.
        :rtype: aiohttp.ClientResponse

        .. code-block:: python

            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                response = await self.client.prompt_object(
                    "ai-data",
                    "receipt_from_la.png",
                    "What is the address of the restaurant?"
                    stream=False
                )

                print(await response.text())

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        check_ssec(ssec)

        headers = cast(DictType, ssec.headers() if ssec else {})
        headers.update(request_headers or {})

        extra_query_params = {"lambdaArn": lambda_arn or ""}

        if version_id:
            extra_query_params["versionId"] = version_id

        prompt_body = kwargs
        prompt_body["prompt"] = prompt

        body = json.dumps(prompt_body)

        return await self._execute(
            "POST",
            bucket_name,
            object_name,
            headers=cast(DictType, headers),
            query_params=cast(DictType, extra_query_params),
            body=body.encode(),
        )

    async def copy_object(
        self,
        bucket_name: str,
        object_name: str,
        source: CopySource,
        sse: Sse | None = None,
        metadata: DictType | None = None,
        tags: Tags | None = None,
        retention: Retention | None = None,
        legal_hold: bool = False,
        metadata_directive: str | None = None,
        tagging_directive: str | None = None,
    ) -> ObjectWriteResult:
        """
        Create an object by server-side copying data from another object.
        In this API maximum supported source object size is 5GiB.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param CopySource source: :class:`CopySource` object.
        :param Sse | None sse: Server-side encryption of destination object.
        :param DictType | None metadata: Any user-defined metadata to be copied along with
                         destination object.
        :param Tags | None tags: Tags for destination object.
        :param Retention | None retention: :class:`Retention` configuration object.
        :param bool legal_hold: Flag to set legal hold for destination object.
        :param str | None metadata_directive: Directive used to handle user metadata for
                                   destination object.
        :param str | None tagging_directive: Directive used to handle tags for destination
                                   object.
        :return: :class:`ObjectWriteResult` object.
        :rtype: ObjectWriteResult
        :raise ValueError: If source is not of type :class:`CopySource`.
        :raise ValueError: If tags is not of type :class:`Tags`.
        :raise ValueError: If retention is not of type :class:`Retention`.
        :raise ValueError: If metadata_directive is not of type :class:`COPY` or
                          :class:`REPLACE`.
        :raise ValueError: If tagging_directive is not of type :class:`COPY` or
                            :class:`REPLACE`.
        :raise ValueError: If source object size is greater than 5GiB.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        if not isinstance(source, CopySource):
            raise ValueError("source must be CopySource type")
        check_sse(sse)
        if tags is not None and not isinstance(tags, Tags):
            raise ValueError("tags must be Tags type")
        if retention is not None and not isinstance(retention, Retention):
            raise ValueError("retention must be Retention type")
        if metadata_directive is not None and metadata_directive not in [COPY, REPLACE]:
            raise ValueError(f"metadata directive must be {COPY} or {REPLACE}")
        if tagging_directive is not None and tagging_directive not in [COPY, REPLACE]:
            raise ValueError(f"tagging directive must be {COPY} or {REPLACE}")

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
            or (size is not None and size > MAX_PART_SIZE)
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
                [ComposeSource.of(source)],
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
        response = await self._execute(
            "PUT",
            bucket_name,
            object_name=object_name,
            headers=headers,
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

    async def _calc_part_count(self, sources: list[ComposeSource]) -> int:
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
            src.build_headers(cast(int, stat.size), cast(str, stat.etag))
            size = cast(int, stat.size)
            if src.length is not None:
                size = src.length
            elif src.offset is not None:
                size -= src.offset

            if size < MIN_PART_SIZE and len(sources) != 1 and i != len(sources):
                raise ValueError(
                    f"source {src.bucket_name}/{src.object_name}: size {size} "
                    f"must be greater than {MIN_PART_SIZE}"
                )

            object_size += size
            if object_size > MAX_MULTIPART_OBJECT_SIZE:
                raise ValueError(
                    f"destination object size must be less than "
                    f"{MAX_MULTIPART_OBJECT_SIZE}"
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
                        f"source {src.bucket_name}/{src.object_name}: "
                        f"for multipart split upload of {size}, "
                        f"last part size is less than {MIN_PART_SIZE}"
                    )
                part_count += count
            else:
                part_count += 1

        if part_count > MAX_MULTIPART_COUNT:
            raise ValueError(
                f"Compose sources create more than allowed multipart "
                f"count {MAX_MULTIPART_COUNT}"
            )
        return part_count

    async def _upload_part_copy(
        self,
        bucket_name: str,
        object_name: str,
        upload_id: str,
        part_number: int,
        headers: DictType,
    ) -> tuple[str, datetime | None]:
        """Execute UploadPartCopy S3 API."""
        response = await self._execute(
            "PUT",
            bucket_name,
            object_name,
            headers=headers,
            query_params={
                "partNumber": str(part_number),
                "uploadId": upload_id,
            },
        )
        return parse_copy_object(await response.text())

    async def compose_object(
        self,
        bucket_name: str,
        object_name: str,
        sources: list[ComposeSource],
        sse: Sse | None = None,
        metadata: DictType | None = None,
        tags: Tags | None = None,
        retention: Retention | None = None,
        legal_hold: bool = False,
    ) -> ObjectWriteResult:
        """
        Create an object by combining data from different source objects using
        server-side copy.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param list[ComposeSource] sources: List of :class:`ComposeSource` object.
        :param Sse | None sse: Server-side encryption of destination object.
        :param DictType | None metadata: Any user-defined metadata to be copied along with
                         destination object.
        :param Tags | None tags: Tags for destination object.
        :param Retention | None retention: :class:`Retention` configuration object.
        :param bool legal_hold: Flag to set legal hold for destination object.
        :return: :class:`ObjectWriteResult` object.
        :rtype: ObjectWriteResult
        :raise ValueError: If sources is not of non-empty type `list` or `tuple`.
        :raise ValueError: If sources is not of type :class:`ComposeSource`.
        :raise ValueError: If tags is not of type :class:`Tags`.
        :raise ValueError: If retention is not of type :class:`Retention`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        if not isinstance(sources, (list, tuple)) or not sources:
            raise ValueError("sources must be non-empty list or tuple type")
        i = 0
        for src in sources:
            if not isinstance(src, ComposeSource):
                raise ValueError(f"sources[{i}] must be ComposeSource type")
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
                size = cast(int, src.object_size)
                if src.length is not None:
                    size = src.length
                elif src.offset is not None:
                    size -= src.offset
                offset = src.offset or 0
                headers = cast(DictType, src.headers)
                headers.update(ssec_headers)
                if size <= MAX_PART_SIZE:
                    part_number += 1
                    if src.length is not None:
                        headers["x-amz-copy-source-range"] = (
                            f"bytes={offset}-{offset + src.length - 1}"
                        )
                    elif src.offset is not None:
                        headers["x-amz-copy-source-range"] = (
                            f"bytes={offset}-{offset + size - 1}"
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
                    length = size if size < MAX_PART_SIZE else MAX_PART_SIZE
                    end_bytes = offset + length - 1
                    headers_copy = headers.copy()
                    headers_copy["x-amz-copy-source-range"] = (
                        f"bytes={offset}-{end_bytes}"
                    )
                    etag, _ = await self._upload_part_copy(
                        bucket_name,
                        object_name,
                        upload_id,
                        part_number,
                        headers_copy,
                    )
                    total_parts.append(Part(part_number, etag))
                    offset += length
                    size -= length
            result = await self._complete_multipart_upload(
                bucket_name,
                object_name,
                upload_id,
                total_parts,
            )
            return ObjectWriteResult(
                cast(str, result.bucket_name),
                cast(str, result.object_name),
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

    async def _abort_multipart_upload(
        self,
        bucket_name: str,
        object_name: str,
        upload_id: str,
    ):
        """Execute AbortMultipartUpload S3 API."""
        await self._execute(
            "DELETE",
            bucket_name,
            object_name,
            query_params={"uploadId": upload_id},
        )

    async def _complete_multipart_upload(
        self,
        bucket_name: str,
        object_name: str,
        upload_id: str,
        parts: list[Part],
    ) -> CompleteMultipartUploadResult:
        """Execute CompleteMultipartUpload S3 API."""
        element = Element("CompleteMultipartUpload")
        for part in parts:
            tag = SubElement(element, "Part")
            SubElement(tag, "PartNumber", str(part.part_number))
            SubElement(tag, "ETag", '"' + part.etag + '"')
        body = getbytes(element)
        response = await self._execute(
            "POST",
            bucket_name,
            object_name,
            body=body,
            headers={
                "Content-Type": "application/xml",
                "Content-MD5": cast(str, md5sum_hash(body)),
            },
            query_params={"uploadId": upload_id},
        )
        return CompleteMultipartUploadResult(response, await response.text())

    async def _create_multipart_upload(
        self,
        bucket_name: str,
        object_name: str,
        headers: DictType,
    ) -> str:
        """Execute CreateMultipartUpload S3 API."""
        if not headers.get("Content-Type"):
            headers["Content-Type"] = "application/octet-stream"
        response = await self._execute(
            "POST",
            bucket_name,
            object_name,
            headers=headers,
            query_params={"uploads": ""},
        )
        element = ET.fromstring(await response.text())
        return cast(str, findtext(element, "UploadId", True))

    async def _put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: Substream,
        headers: DictType | None,
        query_params: DictType | None = None,
    ) -> ObjectWriteResult:
        """Execute PutObject S3 API."""
        response = await self._execute(
            "PUT",
            bucket_name,
            object_name,
            body=data,
            headers=headers,
            query_params=query_params,
            no_body_trace=True,
        )
        return ObjectWriteResult(
            bucket_name,
            object_name,
            response.headers.get("x-amz-version-id"),
            response.headers.get("etag", "").replace('"', ""),
            response.headers,
        )

    async def _upload_part(
        self,
        bucket_name: str,
        object_name: str,
        data: Substream,
        headers: DictType | None,
        upload_id: str,
        part_number: int,
        semaphore: asyncio.Semaphore | None = None,
    ) -> str:
        """Execute UploadPart S3 API."""

        async def get_result():
            return await self._put_object(
                bucket_name,
                object_name,
                data,
                headers,
                query_params={
                    "partNumber": str(part_number),
                    "uploadId": upload_id,
                },
            )

        if semaphore:
            async with semaphore:
                return cast(str, (await get_result()).etag)
        else:
            return cast(str, (await get_result()).etag)

    async def _upload_part_task(self, args):
        """Upload_part task for CoroutinePool."""
        return args[5], await self._upload_part(*args)

    async def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
        metadata: DictType | None = None,
        sse: Sse | None = None,
        progress: ProgressType | None = None,
        part_size: int = 0,
        num_parallel_uploads: int = 3,
        tags: Tags | None = None,
        retention: Retention | None = None,
        legal_hold: bool = False,
    ) -> ObjectWriteResult:
        """
        Uploads data from a stream to an object in a bucket.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param BinaryIO | FileIOWrapperBase data: An object having callable read() returning bytes object.
        :param int length: Data size; -1 for unknown size and set valid part_size.
        :param str content_type: Content type of the object.
        :param DictType | None metadata: Any additional metadata to be uploaded along
            with your PUT request.
        :param Sse | None sse: Server-side encryption.
        :param ProgressType | None progress: A progress object.
        :param int part_size: Multipart part size.
        :param int num_parallel_uploads: Number of parallel uploads.
        :param Tags | None tags: :class:`Tags` for the object.
        :param Retention | None retention: :class:`Retention` configuration object.
        :param bool legal_hold: Flag to set legal hold for the object.
        :return: :class:`ObjectWriteResult` object.
        :rtype: ObjectWriteResult
        :raise ValueError: If tags is not of type :class:`Tags`.
        :raise ValueError: If retention is not of type :class:`Retention`.
        :raise ValueError: If input data doesn't have callable `read()`.
        :raise IOError: If input data doesn't have enough data to read.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        check_sse(sse)
        if tags is not None and not isinstance(tags, Tags):
            raise ValueError("tags must be Tags type")
        if retention is not None and not isinstance(retention, Retention):
            raise ValueError("retention must be Retention type")
        if not callable(getattr(data, "read")):
            raise ValueError("input data must have callable read()")
        part_size, part_count = get_part_info(length, part_size)
        if progress:
            # Set progress bar length and object name before upload
            await progress.set_meta(object_name=object_name, total_length=length)

        headers = genheaders(metadata, sse, tags, retention, legal_hold)
        headers["Content-Type"] = content_type or "application/octet-stream"

        object_size = length
        uploaded_size = 0
        part_number = 0
        stop = False
        upload_id = None
        parts = []
        parallel_tasks = []
        semaphore: asyncio.Semaphore | None = None

        try:
            while not stop:
                part_number += 1
                if part_count > 0:
                    if part_number == part_count:
                        part_size = object_size - uploaded_size
                        stop = True
                    part_data = Substream(data, uploaded_size, part_size)
                    if part_data.size != part_size:
                        raise IOError(
                            f"stream having not enough data;"
                            f"expected: {part_size}, "
                            f"got: {part_data.size} bytes"
                        )
                else:
                    part_data = Substream(data, uploaded_size, part_size)
                    if part_data.size == 0:
                        break
                    if part_data.size < part_size:
                        part_count = part_number
                        stop = True
                        part_size = part_data.size

                if progress:
                    await progress.update(part_size)

                uploaded_size += part_size

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
                    if num_parallel_uploads and num_parallel_uploads > 1:
                        semaphore = asyncio.Semaphore(num_parallel_uploads)

                args = (
                    bucket_name,
                    object_name,
                    part_data,
                    (
                        cast(DictType, sse.headers())
                        if isinstance(sse, SseCustomerKey)
                        else None
                    ),
                    upload_id,
                    part_number,
                    semaphore,
                )
                if num_parallel_uploads > 1:
                    parallel_tasks.append(
                        asyncio.create_task(self._upload_part_task(args))
                    )
                else:
                    etag = await self._upload_part(*args)
                    parts.append(Part(part_number, etag))

            if semaphore:
                result = await asyncio.gather(*parallel_tasks)
                parts = [Part(0, "")] * part_count
                while len(result) > 0:
                    part_number, etag = result.pop(0)
                    parts[part_number - 1] = Part(part_number, etag)

            upload_result = await self._complete_multipart_upload(
                bucket_name,
                object_name,
                cast(str, upload_id),
                parts,
            )
            return ObjectWriteResult(
                cast(str, upload_result.bucket_name),
                cast(str, upload_result.object_name),
                upload_result.version_id,
                upload_result.etag,
                upload_result.http_headers,
                location=upload_result.location,
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
        bucket_name: str,
        prefix: str | None = None,
        recursive: bool = False,
        start_after: str | None = None,
        include_user_meta: bool = False,
        include_version: bool = False,
        use_api_v1: bool = False,
        use_url_encoding_type: bool = True,
        fetch_owner: bool = False,
        extra_headers: DictType | None = None,
    ) -> ListObjects:
        """
        Lists object information of a bucket.

        :param str bucket_name: Name of the bucket.
        :param str | None prefix: Object name starts with prefix.
        :param bool recursive: List recursively than directory structure emulation.
        :param str | None start_after: List objects after this key name.
        :param bool include_user_meta: MinIO specific flag to control to include
                                 user metadata.
        :param bool include_version: Flag to control whether include object
                                versions.
        :param bool use_api_v1: Flag to control to use ListObjectV1 S3 API or not.
        :param bool use_url_encoding_type: Flag to control whether URL encoding type
                                      to be used or not.
        :param bool fetch_owner: Flag to control whether to fetch owner information.
        :param DictType | None extra_headers: Any additional headers to be added with GET request.
        :param DictType | None extra_query_params: Extra query parameters for advanced usage.
        :return: Iterator of :class:`Object`.
        :rtype: ListObjects

        .. code-block:: python

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

            asyncio.run(main())
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
            fetch_owner=fetch_owner,
            extra_headers=extra_headers,
        )

    async def stat_object(
        self,
        bucket_name: str,
        object_name: str,
        ssec: SseCustomerKey | None = None,
        version_id: str | None = None,
        extra_headers: DictType | None = None,
        extra_query_params: DictType | None = None,
    ) -> Object:
        """
        Get object information and metadata of an object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param SseCustomerKey | None ssec: Server-side encryption customer key.
        :param str | None version_id: Version ID of the object.
        :param DictType | None request_headers: Any additional headers to be added with GET request.
        :param DictType | None extra_query_params: Extra query parameters for advanced usage.
        :return: :class:`Object`.
        :rtype: Object

        .. code-block:: python

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

            asyncio.run(main())
        """

        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        check_ssec(ssec)

        headers = cast(DictType, ssec.headers() if ssec else {})
        if extra_headers:
            headers.update(extra_headers)

        query_params = extra_query_params or {}
        query_params.update({"versionId": version_id} if version_id else {})
        response = await self._execute(
            "HEAD",
            bucket_name,
            object_name,
            headers=headers,
            query_params=query_params,
        )

        value = response.headers.get("last-modified")
        if value is not None:
            last_modified = time.from_http_header(value)
        else:
            last_modified = None

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

    async def remove_object(
        self, bucket_name: str, object_name: str, version_id: str | None = None
    ):
        """
        Remove an object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str | None version_id: Version ID of the object.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        await self._execute(
            "DELETE",
            bucket_name,
            object_name,
            query_params={"versionId": version_id} if version_id else None,
        )

    async def _delete_objects(
        self,
        bucket_name: str,
        delete_object_list: list[DeleteObject],
        quiet: bool = False,
        bypass_governance_mode: bool = False,
    ) -> DeleteResult:
        """
        Delete multiple objects.

        :param str bucket_name: Name of the bucket.
        :param list[DeleteObject] delete_object_list: List of maximum 1000
            :class:`DeleteObject` object.
        :param bool quiet: quiet flag.
        :param bool bypass_governance_mode: Bypass Governance retention mode.
        :return: :class:`DeleteResult` object.
        :rtype: DeleteResult
        """
        body = marshal(DeleteRequest(delete_object_list, quiet=quiet))
        headers: DictType = {
            "Content-MD5": cast(str, md5sum_hash(body)),
        }
        if bypass_governance_mode:
            headers["x-amz-bypass-governance-retention"] = "true"
        response = await self._execute(
            "POST",
            bucket_name,
            body=body,
            headers=headers,
            query_params={"delete": ""},
        )

        element = ET.fromstring(await response.text())
        return (
            DeleteResult([], [DeleteError.fromxml(element)])
            if element.tag.endswith("Error")
            else unmarshal(DeleteResult, await response.text())
        )

    def remove_objects(
        self,
        bucket_name: str,
        delete_object_list: Iterable[DeleteObject],
        bypass_governance_mode: bool = False,
    ) -> DeleteErrors:
        """
        Remove multiple objects.

        :param str bucket_name: Name of the bucket.
        :param Iterable[DeleteObject] delete_object_list: An iterable containing
            :class:`DeleteObject` object.
        :param bool bypass_governance_mode: Bypass Governance retention mode.
        :return: A :class:`DeleteErrors` object to be an async generator and list.
        :rtype: DeleteErrors

        .. code-block:: python

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

                # As async generator
                print('example two')
                async for error in client.remove_objects(
                    "my-bucket",
                    [
                        DeleteObject("my-object1"),
                        DeleteObject("my-object2"),
                        DeleteObject("my-object3",
                        "13f88b18-8dcd-4c83-88f2-8631fdb6250c"),
                    ],
                ):
                    print("error occured when deleting object", error)

                # Remove a prefix recursively.
                print('example three')
                delete_object_list = [DeleteObject(obj.object_name)
                    for obj in await client.list_objects(
                        "my-bucket",
                        "my/prefix/",
                        recursive=True
                    )
                ]
                errors = await client.remove_objects("my-bucket", delete_object_list)
                for error in errors:
                    print("error occured when deleting object", error)

            asyncio.run(main())
        """
        return DeleteErrors(
            client=self,
            bucket_name=bucket_name,
            delete_object_list=delete_object_list,
            bypass_governance_mode=bypass_governance_mode,
        )

    async def get_presigned_url(
        self,
        method: str,
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(days=7),
        response_headers: DictType | None = None,
        request_date: datetime | None = None,
        version_id: str | None = None,
        extra_query_params: DictType | None = None,
    ) -> str:
        """
        Get presigned URL of an object for HTTP method, expiry time and custom
        request parameters.

        :param str method: HTTP method.
        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param datetime.timedelta expires: Expiry in seconds; defaults to 7 days.
        :param DictType | None response_headers: Optional response_headers argument to
                                 specify response fields like date, size,
                                 type of file, data about server, etc.
        :param datetime.timedelta request_date: Optional request_date argument to
                             specify a different request date. Default is
                             current date.
        :param str | None version_id: Version ID of the object.
        :param DictType | None extra_query_params: Extra query parameters for advanced usage.
        :return: URL string.
        :rtype: str
        :raise ValueError: If expires is not between 1 second to 7 days.

        .. code-block:: python

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


            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        if expires.total_seconds() < 1 or expires.total_seconds() > 604800:
            raise ValueError("expires must be between 1 second to 7 days")

        region = await self._get_region(bucket_name)
        query_params = extra_query_params or {}
        query_params.update({"versionId": version_id} if version_id else {})
        query_params.update(response_headers or {})
        creds = await self._provider.retrieve() if self._provider else None
        if creds and creds.session_token:
            query_params["X-Amz-Security-Token"] = creds.session_token

        if self._server_url:
            base_url = self._server_url
        else:
            base_url = self._base_url
        url = base_url.build(
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
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(days=7),
        response_headers: DictType | None = None,
        request_date: datetime | None = None,
        version_id: str | None = None,
        extra_query_params: DictType | None = None,
    ) -> str:
        """
        Get presigned URL of an object to download its data with expiry time
        and custom request parameters.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param datetime.timedelta expires: Expiry in seconds; defaults to 7 days.
        :param DictType | None response_headers: Optional response_headers argument to
                                  specify response fields like date, size,
                                  type of file, data about server, etc.
        :param datetime.timedelta request_date: Optional request_date argument to
                              specify a different request date. Default is
                              current date.
        :param str | None version_id: Version ID of the object.
        :param DictType | None extra_query_params: Extra query parameters for advanced usage.
        :return: URL string.
        :rtype: str

        .. code-block:: python

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


            asyncio.run(main())
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
        )

    async def presigned_put_object(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta = timedelta(days=7),
    ) -> str:
        """
        Get presigned URL of an object to upload data with expiry time and
        custom request parameters.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param datetime.timedelta expires: Expiry in seconds; defaults to 7 days.
        :return: URL string.
        :rtype: str

        .. code-block:: python

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

            asyncio.run(main())
        """
        return await self.get_presigned_url(
            "PUT",
            bucket_name,
            object_name,
            expires,
        )

    async def presigned_post_policy(self, policy: PostPolicy) -> dict[str, str]:
        """
        Get form-data of PostPolicy of an object to upload its data using POST
        method.

        :param PostPolicy policy: :class:`PostPolicy`.
        :return: dict contains form-data.
        :rtype: dict[str, str]
        :raise ValueError: If policy is not of type :class:`PostPolicy`.
        :raise ValueError: If the access is anonymous.

        .. code-block:: python

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

            asyncio.run(main())
        """
        if not isinstance(policy, PostPolicy):
            raise ValueError("policy must be PostPolicy type")
        if not self._provider:
            raise ValueError(
                "anonymous access does not require presigned post form-data",
            )
        return policy.form_data(
            await self._provider.retrieve(),
            await self._get_region(policy.bucket_name),
        )

    async def delete_bucket_replication(self, bucket_name: str):
        """
        Delete replication configuration of a bucket.

        :param str bucket_name: Name of the bucket.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        await self._execute("DELETE", bucket_name, query_params={"replication": ""})

    async def get_bucket_replication(
        self, bucket_name: str
    ) -> ReplicationConfig | None:
        """
        Get bucket replication configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :return: :class:`ReplicationConfig` object.
        :rtype: ReplicationConfig | None
        :raise S3Error: If the replication configuration is not found.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        try:
            response = await self._execute(
                "GET",
                bucket_name,
                query_params={"replication": ""},
            )
            return unmarshal(ReplicationConfig, await response.text())
        except S3Error as exc:
            if exc.code != "ReplicationConfigurationNotFoundError":
                raise
        return None

    async def set_bucket_replication(
        self,
        bucket_name: str,
        config: ReplicationConfig,
    ):
        """
        Set bucket replication configuration to a bucket.

        :param str bucket_name: Name of the bucket.
        :param ReplicationConfig config: :class:`ReplicationConfig` object.
        :raise ValueError: If config is not of type :class:`ReplicationConfig`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        if not isinstance(config, ReplicationConfig):
            raise ValueError("config must be ReplicationConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params={"replication": ""},
        )

    async def delete_bucket_lifecycle(self, bucket_name: str):
        """
        Delete notification configuration of a bucket.

        :param str bucket_name: Name of the bucket.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        await self._execute("DELETE", bucket_name, query_params={"lifecycle": ""})

    async def get_bucket_lifecycle(self, bucket_name: str) -> LifecycleConfig | None:
        """
        Get bucket lifecycle configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :return: :class:`LifecycleConfig` object.
        :rtype: LifecycleConfig | None
        :raise S3Error: If the lifecycle configuration is not found.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        try:
            response = await self._execute(
                "GET", bucket_name, query_params={"lifecycle": ""}
            )
            return unmarshal(LifecycleConfig, await response.text())
        except S3Error as exc:
            if exc.code != "NoSuchLifecycleConfiguration":
                raise
        return None

    async def set_bucket_lifecycle(
        self,
        bucket_name: str,
        config: LifecycleConfig,
    ):
        """
        Set bucket lifecycle configuration to a bucket.

        :param str bucket_name: Name of the bucket.
        :param LifecycleConfig config: :class:`LifecycleConfig` object.
        :raise ValueError: If config is not of type :class:`LifecycleConfig`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        if not isinstance(config, LifecycleConfig):
            raise ValueError("config must be LifecycleConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params={"lifecycle": ""},
        )

    async def delete_bucket_tags(self, bucket_name: str):
        """
        Delete tags configuration of a bucket.

        :param str bucket_name: Name of the bucket.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        await self._execute("DELETE", bucket_name, query_params={"tagging": ""})

    async def get_bucket_tags(self, bucket_name: str) -> Tags | None:
        """
        Get tags configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :return: :class:`Tags` object.
        :rtype: Tags | None
        :raise S3Error: If the tags configuration is not found.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        try:
            response = await self._execute(
                "GET", bucket_name, query_params={"tagging": ""}
            )
            tagging = unmarshal(Tagging, await response.text())
            return tagging.tags
        except S3Error as exc:
            if exc.code != "NoSuchTagSet":
                raise
        return None

    async def set_bucket_tags(self, bucket_name: str, tags: Tags):
        """
        Set tags configuration to a bucket.

        :param str bucket_name: Name of the bucket.
        :param Tags tags: :class:`Tags` object.
        :raise ValueError: If tags is not of type :class:`Tags`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        if not isinstance(tags, Tags):
            raise ValueError("tags must be Tags type")
        body = marshal(Tagging(tags))
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params={"tagging": ""},
        )

    async def delete_object_tags(
        self,
        bucket_name: str,
        object_name: str,
        version_id: str | None = None,
    ):
        """
        Delete tags configuration of an object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str | None version_id: Version ID of the Object.

        .. code-block:: python

            from miniopy_async import Minio
            import asyncio

            client = Minio(
                "play.min.io",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
                secure=True  # http for False, https for True
            )

            async def main():
                await client.delete_object_tags("my-bucket", "my-object")

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        query_params = {"versionId": version_id} if version_id else {}
        query_params["tagging"] = ""
        await self._execute(
            "DELETE",
            bucket_name,
            object_name=object_name,
            query_params=cast(DictType, query_params),
        )

    async def get_object_tags(
        self,
        bucket_name: str,
        object_name: str,
        version_id: str | None = None,
    ) -> Tags | None:
        """
        Get tags configuration of a object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str | None version_id: Version ID of the Object.
        :return: :class:`Tags` object.
        :rtype: Tags | None
        :raise S3Error: If the tags configuration is not found.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        query_params = {"versionId": version_id} if version_id else {}
        query_params["tagging"] = ""
        try:
            response = await self._execute(
                "GET",
                bucket_name,
                object_name=object_name,
                query_params=cast(DictType, query_params),
            )
            tagging = unmarshal(Tagging, await response.text())
            return tagging.tags
        except S3Error as exc:
            if exc.code != "NoSuchTagSet":
                raise
        return None

    async def set_object_tags(
        self,
        bucket_name: str,
        object_name: str,
        tags: Tags,
        version_id: str | None = None,
    ):
        """
        Set tags configuration to an object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param Tags version_id: Version ID of the Object.
        :param str | None tags: :class:`Tags` object.
        :raise ValueError: If tags is not of type :class:`Tags`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
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
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params=cast(DictType, query_params),
        )

    async def enable_object_legal_hold(
        self,
        bucket_name: str,
        object_name: str,
        version_id: str | None = None,
    ):
        """
        Enable legal hold on an object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str | None version_id: Version ID of the object.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        body = marshal(LegalHold(True))
        query_params = {"versionId": version_id} if version_id else {}
        query_params["legal-hold"] = ""
        await self._execute(
            "PUT",
            bucket_name,
            object_name=object_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params=cast(DictType, query_params),
        )

    async def disable_object_legal_hold(
        self,
        bucket_name: str,
        object_name: str,
        version_id: str | None = None,
    ):
        """
        Disable legal hold on an object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str | None version_id: Version ID of the object.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        body = marshal(LegalHold(False))
        query_params = {"versionId": version_id} if version_id else {}
        query_params["legal-hold"] = ""
        await self._execute(
            "PUT",
            bucket_name,
            object_name=object_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params=cast(DictType, query_params),
        )

    async def is_object_legal_hold_enabled(
        self,
        bucket_name: str,
        object_name: str,
        version_id: str | None = None,
    ) -> bool:
        """
        Returns true if legal hold is enabled on an object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str | None version_id: Version ID of the object.
        :return: Whether the legal hold is enabled or not.
        :rtype: bool
        :raise S3Error: If the object lock configuration is not found.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        query_params = {"versionId": version_id} if version_id else {}
        query_params["legal-hold"] = ""
        try:
            response = await self._execute(
                "GET",
                bucket_name,
                object_name=object_name,
                query_params=cast(DictType, query_params),
            )
            legal_hold = unmarshal(LegalHold, await response.text())
            return legal_hold.status
        except S3Error as exc:
            if exc.code != "NoSuchObjectLockConfiguration":
                raise
        return False

    async def delete_object_lock_config(self, bucket_name: str):
        """
        Delete object-lock configuration of a bucket.

        :param str bucket_name: Name of the bucket.

        .. code-block:: python

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

            asyncio.run(main())
        """
        await self.set_object_lock_config(
            bucket_name, ObjectLockConfig(None, None, None)
        )

    async def get_object_lock_config(self, bucket_name: str) -> ObjectLockConfig:
        """
        Get object-lock configuration of a bucket.

        :param str bucket_name: Name of the bucket.
        :return: :class:`ObjectLockConfig` object.
        :rtype: ObjectLockConfig

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        response = await self._execute(
            "GET", bucket_name, query_params={"object-lock": ""}
        )
        return unmarshal(ObjectLockConfig, await response.text())

    async def set_object_lock_config(
        self,
        bucket_name: str,
        config: ObjectLockConfig,
    ):
        """
        Set object-lock configuration to a bucket.

        :param str bucket_name: Name of the bucket.
        :param ObjectLockConfig config: :class:`ObjectLockConfig` object.
        :raise ValueError: If config is not of type :class:`ObjectLockConfig`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        if not isinstance(config, ObjectLockConfig):
            raise ValueError("config must be ObjectLockConfig type")
        body = marshal(config)
        await self._execute(
            "PUT",
            bucket_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params={"object-lock": ""},
        )

    async def get_object_retention(
        self,
        bucket_name: str,
        object_name: str,
        version_id: str | None = None,
    ) -> Retention | None:
        """
        Get retention configuration of an object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param str | None version_id: Version ID of the object.
        :return: :class:`Retention` object.
        :rtype: Retention | None
        :raise S3Error: If the object lock configuration is not found.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        query_params = {"versionId": version_id} if version_id else {}
        query_params["retention"] = ""
        try:
            response = await self._execute(
                "GET",
                bucket_name,
                object_name=object_name,
                query_params=cast(DictType, query_params),
            )
            return unmarshal(Retention, await response.text())
        except S3Error as exc:
            if exc.code != "NoSuchObjectLockConfiguration":
                raise
        return None

    async def set_object_retention(
        self,
        bucket_name: str,
        object_name: str,
        config: Retention,
        version_id: str | None = None,
    ):
        """
        Set retention configuration on an object.

        :param str bucket_name: Name of the bucket.
        :param str object_name: Object name in the bucket.
        :param Retention config: :class:`Retention` object.
        :param str | None version_id: Version ID of the object.
        :raise ValueError: If config is not of type :class:`Retention`.

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)
        check_object_name(object_name)
        if not isinstance(config, Retention):
            raise ValueError("config must be Retention type")
        body = marshal(config)
        query_params = {"versionId": version_id} if version_id else {}
        query_params["retention"] = ""
        await self._execute(
            "PUT",
            bucket_name,
            object_name=object_name,
            body=body,
            headers={"Content-MD5": cast(str, md5sum_hash(body))},
            query_params=cast(DictType, query_params),
        )

    async def upload_snowball_objects(
        self,
        bucket_name: str,
        object_list: Iterable[SnowballObject],
        object_name: str | None = None,
        metadata: DictType | None = None,
        sse: Sse | None = None,
        tags: Tags | None = None,
        retention: Retention | None = None,
        legal_hold: bool = False,
        staging_filename: str | None = None,
        compression: bool = False,
    ) -> ObjectWriteResult:
        """
        Uploads multiple objects in a single put call. It is done by creating
        intermediate TAR file optionally compressed which is uploaded to S3
        service.

        :param str bucket_name: Name of the bucket.
        :param Iterable[SnowballObject] object_list: An iterable containing
            :class:`SnowballObject` object.
        :param str object_name: Optional name for the uploaded TAR archive.
            If not provided, a random name in the format `snowball.<random>.tar` will be used.
        :param DictType | None metadata: Any additional metadata to be uploaded along
            with your PUT request.
        :param Sse | None sse: Server-side encryption.
        :param Tags | None tags: :class:`Tags` for the object.
        :param Retention | None retention: :class:`Retention` configuration object.
        :param bool legal_hold: Flag to set legal hold for the object.
        :param str | None staging_filename: A staging filename to create intermediate tarball.
        :param bool compression: Flag to compress TAR ball.
        :return: :class:`ObjectWriteResult` object.
        :rtype: ObjectWriteResult

        .. code-block:: python

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

            asyncio.run(main())
        """
        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)

        object_name = object_name or f"snowball.{random()}.tar"

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
                    info.size = cast(int, obj.length)
                    info.mtime = int(
                        time.to_float(obj.mod_time or time.utcnow()),
                    )
                    tar.addfile(info, obj.data)

        if not name:
            length = cast(BytesIO, fileobj).tell()
            cast(BytesIO, fileobj).seek(0)
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
            cast(BinaryIO, fileobj),
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
        bucket_name: str,
        continuation_token: str | None = None,  # listV2 only
        delimiter: str | None = None,  # all
        encoding_type: str | None = None,  # all
        fetch_owner: bool | None = None,  # listV2 only
        include_user_meta: bool = False,  # MinIO specific listV2.
        max_keys: int | None = None,  # all
        prefix: str | None = None,  # all
        start_after: str | None = None,
        # all: v1:marker, versioned:key_marker
        version_id_marker: str | None = None,  # versioned
        use_api_v1: bool = False,
        include_version: bool = False,
        extra_headers: DictType | None = None,
    ) -> AsyncGenerator[Object]:
        """
        List objects optionally including versions.
        Note: Its required to send empty values to delimiter/prefix and 1000 to
        max-keys when not provided for server-side bucket policy evaluation to
        succeed; otherwise AccessDenied error will be returned for such
        policies.
        """

        check_bucket_name(bucket_name, s3_check=self._base_url.is_aws_host)

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

            response = await self._execute(
                "GET",
                bucket_name,
                query_params=query,
                headers=extra_headers,
            )

            (
                objects,
                is_truncated,
                start_after,
                version_id_marker,
            ) = parse_list_objects(await response.text())

            if not include_version:
                version_id_marker = None
                if not use_api_v1:
                    continuation_token = start_after

            for object in objects:
                yield object

    async def _list_multipart_uploads(
        self,
        bucket_name: str,
        delimiter: str | None = None,
        encoding_type: str | None = None,
        key_marker: str | None = None,
        max_uploads: int | None = None,
        prefix: str | None = None,
        upload_id_marker: str | None = None,
        extra_headers: DictType | None = None,
        extra_query_params: DictType | None = None,
    ) -> ListMultipartUploadsResult:
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
            :class:`ListMultipartUploadsResult`
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

        response = await self._execute(
            "GET",
            bucket_name,
            query_params=query_params,
            headers=extra_headers,
        )
        return ListMultipartUploadsResult(await response.text())

    async def _list_parts(
        self,
        bucket_name: str,
        object_name: str,
        upload_id: str,
        max_parts: int | None = None,
        part_number_marker: str | None = None,
        extra_headers: DictType | None = None,
        extra_query_params: DictType | None = None,
    ) -> ListPartsResult:
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
        :return: :class:`ListPartsResult` object
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

        response = await self._execute(
            "GET",
            bucket_name,
            object_name=object_name,
            query_params=query_params,
            headers=extra_headers,
        )
        return ListPartsResult(await response.text())
