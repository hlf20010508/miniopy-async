# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
# (C) 2020 MinIO, Inc.
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

"""Time formatter for S3 APIs."""

from __future__ import absolute_import, annotations

import locale
from contextlib import contextmanager
import time as ctime
from datetime import datetime, timezone
from typing import Generator
import sys

if sys.version_info > (3, 11):
    from datetime import UTC

from . import __LOCALE_LOCK__

_HTTP_HEADER_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


@contextmanager
def _set_locale(name: str) -> Generator[str]:
    """Thread-safe wrapper to locale.setlocale()."""
    with __LOCALE_LOCK__:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)


def _to_utc(value: datetime) -> datetime:
    """Convert to UTC time if value is not naive."""
    return (
        value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    )


def from_iso8601utc(value: str | None) -> datetime | None:
    """Parse UTC ISO-8601 formatted string to datetime."""
    if value is None:
        return None

    try:
        time = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        time = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return time.replace(tzinfo=timezone.utc)


def to_iso8601utc(value: datetime | None) -> str | None:
    """Format datetime into UTC ISO-8601 formatted string."""
    if value is None:
        return None

    value = _to_utc(value)
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + value.strftime("%f")[:3] + "Z"


def from_http_header(value: str) -> datetime:
    """Parse HTTP header date formatted string to datetime."""
    with _set_locale("C"):
        return datetime.strptime(
            value,
            _HTTP_HEADER_FORMAT,
        ).replace(tzinfo=timezone.utc)


def to_http_header(value: datetime) -> str:
    """Format datatime into HTTP header date formatted string."""
    with _set_locale("C"):
        return _to_utc(value).strftime(_HTTP_HEADER_FORMAT)


def to_amz_date(value: datetime) -> str:
    """Format datetime into AMZ date formatted string."""
    return _to_utc(value).strftime("%Y%m%dT%H%M%SZ")


def utcnow() -> datetime:
    """Timezone-aware wrapper to datetime.utcnow()."""
    if sys.version_info > (3, 11):
        return datetime.now(UTC)
    else:
        return datetime.utcnow().replace(tzinfo=timezone.utc)


def to_signer_date(value: datetime) -> str:
    """Format datetime into SignatureV4 date formatted string."""
    return _to_utc(value).strftime("%Y%m%d")


def to_float(value: datetime) -> float:
    """Convert datetime into float value."""
    return ctime.mktime(value.timetuple()) + value.microsecond * 1e-6
