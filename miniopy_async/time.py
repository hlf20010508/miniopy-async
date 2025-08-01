# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage, (C)
# 2020 MinIO, Inc.
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

import sys
import time as ctime
from datetime import datetime, timezone

if sys.version_info > (3, 11):
    from datetime import UTC

_WEEK_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


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
    if len(value) != 29:
        raise ValueError(f"time data {value} does not match HTTP header format")

    if value[0:3] not in _WEEK_DAYS or value[3] != ",":
        raise ValueError(f"time data {value} does not match HTTP header format")
    weekday = _WEEK_DAYS.index(value[0:3])

    if value[4] != " " or value[7] != " ":
        raise ValueError(f"time data {value} does not match HTTP header format")
    day = int(value[5:7])

    if value[8:11] not in _MONTHS:
        raise ValueError(f"time data {value} does not match HTTP header format")
    month = _MONTHS.index(value[8:11])

    time = datetime.strptime(value[11:], " %Y %H:%M:%S GMT")
    time = time.replace(day=day, month=month + 1, tzinfo=timezone.utc)

    if weekday != time.weekday():
        raise ValueError(f"time data {value} does not match HTTP header format")

    return time


def to_http_header(value: datetime) -> str:
    """Format datatime into HTTP header date formatted string."""
    value = _to_utc(value)
    weekday = _WEEK_DAYS[value.weekday()]
    day = value.strftime(" %d ")
    month = _MONTHS[value.month - 1]
    suffix = value.strftime(" %Y %H:%M:%S GMT")
    return f"{weekday},{day}{month}{suffix}"


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
