# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
# (C) 2015-2019 MinIO, Inc.
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

# pylint: disable=too-many-lines

"""
miniopy_async.error
~~~~~~~~~~~~~~~~~~~

This module provides custom exception classes for MinIO library
and API specific errors.

:copyright:
(C) 2015, 2016, 2017 by MinIO, Inc.
(C) 2022 Huseyn Mashadiyev <mashadiyev.huseyn@gmail.com>
(C) 2022 L-ING <hlf01@icloud.com>
:license: Apache 2.0, see LICENSE for more details.

"""

from xml.etree import ElementTree as ET

from .xml import findtext


class MinioException(Exception):
    """Base Minio exception."""


class InvalidResponseError(MinioException):
    """Raised to indicate that non-xml response from server."""

    def __init__(self, code, content_type, body):
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

    def __init__(self, message, status_code):
        self._status_code = status_code
        super().__init__(message)

    @property
    def status_code(self):
        """Get HTTP status code."""
        return self._status_code


class S3Error(MinioException):
    """
    Raised to indicate that error response is received
    when executing S3 operation.
    """

    def __init__(
        self,
        code,
        message,
        resource,
        request_id,
        host_id,
        response,
        bucket_name=None,
        object_name=None,
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
    def code(self):
        """Get S3 error code."""
        return self._code

    @property
    def message(self):
        """Get S3 error message."""
        return self._message

    @property
    def response(self):
        """Get HTTP response."""
        return self._response

    @classmethod
    def fromxml(cls, response, response_data):
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

    def copy(self, code, message):
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
