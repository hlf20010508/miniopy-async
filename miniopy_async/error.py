# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage, (C)
# (C) 2015-2019 MinIO, Inc.
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

# pylint: disable=too-many-lines

"""This module provides custom exception classes for MinIO library and API specific errors."""

from __future__ import absolute_import, annotations

from typing import Type, TypeVar
from xml.etree import ElementTree as ET

from aiohttp import ClientResponse

from .xml import findtext


class MinioException(Exception):
    """Base Minio exception."""


class InvalidResponseError(MinioException):
    """Raised to indicate that non-xml response from server."""

    def __init__(self, code: int, content_type: str | None, body: str | None):
        self._code = code
        self._content_type = content_type
        self._body = body
        super().__init__(
            f"non-XML response from server; "
            f"Response code: {code}, Content-Type: {content_type}, Body: {body}"
        )

    def __reduce__(self):
        return type(self), (self._code, self._content_type, self._body)


class ServerError(MinioException):
    """Raised to indicate that S3 service returning HTTP server error."""

    def __init__(self, message: str, status_code: int):
        self._status_code = status_code
        super().__init__(message)

    @property
    def status_code(self) -> int:
        """Get HTTP status code."""
        return self._status_code


A = TypeVar("A", bound="S3Error")


class S3Error(MinioException):
    """
    Raised to indicate that error response is received
    when executing S3 operation.
    """

    def __init__(
        self,
        code: str | None,
        message: str | None,
        resource: str | None,
        request_id: str | None,
        host_id: str | None,
        response: ClientResponse,
        bucket_name: str | None = None,
        object_name: str | None = None,
    ):
        self._code = code
        self._message = message
        self._resource = resource
        self._request_id = request_id
        self._host_id = host_id
        self._response = response
        self._bucket_name = bucket_name
        self._object_name = object_name

        bucket_message = (
            (", bucket_name: " + self._bucket_name) if self._bucket_name else ""
        )
        object_message = (
            (", object_name: " + self._object_name) if self._object_name else ""
        )
        super().__init__(
            f"S3 operation failed; code: {code}, message: {message}, "
            f"resource: {resource}, request_id: {request_id}, "
            f"host_id: {host_id}{bucket_message}{object_message}"
        )

    def __reduce__(self):
        return type(self), (
            self._code,
            self._message,
            self._resource,
            self._request_id,
            self._host_id,
            self._response,
            self._bucket_name,
            self._object_name,
        )

    @property
    def code(self) -> str | None:
        """Get S3 error code."""
        return self._code

    @property
    def message(self) -> str | None:
        """Get S3 error message."""
        return self._message

    @property
    def response(self) -> ClientResponse:
        """Get HTTP response."""
        return self._response

    @classmethod
    def fromxml(cls: Type[A], response: ClientResponse, response_data: str) -> A:
        """Create new object with values from XML element."""
        element = ET.fromstring(response_data)
        return cls(
            findtext(element, "Code"),
            findtext(element, "Message"),
            findtext(element, "Resource"),
            findtext(element, "RequestId"),
            findtext(element, "HostId"),
            bucket_name=findtext(element, "BucketName"),
            object_name=findtext(element, "Key"),
            response=response,
        )

    def copy(self, code: str, message: str) -> "S3Error":
        """Make a copy with replace code and message."""
        return S3Error(
            code,
            message,
            self._resource,
            self._request_id,
            self._host_id,
            self._response,
            self._bucket_name,
            self._object_name,
        )


class MinioAdminException(Exception):
    """Raised to indicate admin API execution error."""

    def __init__(self, code: str, body: str):
        self._code = code
        self._body = body
        super().__init__(
            f"admin request failed; Status: {code}, Body: {body}",
        )

    def __reduce__(self):
        return type(self), (self._code, self._body)


class UnreachableError(MinioException):
    """Raised when unreachable code reached."""

    def __init__(self):
        super().__init__("unreachable code reached, please report this issue.")
