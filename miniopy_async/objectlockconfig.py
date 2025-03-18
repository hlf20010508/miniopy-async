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

"""
Request/response of PutObjectLockConfiguration and GetObjectLockConfiguration
APIs.
"""

from __future__ import absolute_import, annotations

from typing import Type, TypeVar
from xml.etree import ElementTree as ET

from .commonconfig import COMPLIANCE, ENABLED, GOVERNANCE
from .xml import Element, SubElement, find, findtext

DAYS = "Days"
YEARS = "Years"

A = TypeVar("A", bound="ObjectLockConfig")


class ObjectLockConfig:
    """Object lock configuration."""

    def __init__(
        self,
        mode: str | None,
        duration: int | None,
        duration_unit: str | None,
    ):
        if (mode is not None) ^ (duration is not None):
            if mode is None:
                raise ValueError("mode must be provided")
            raise ValueError("duration must be provided")
        if mode is not None and mode not in [GOVERNANCE, COMPLIANCE]:
            raise ValueError(
                "mode must be {0} or {1}".format(GOVERNANCE, COMPLIANCE),
            )
        if duration_unit:
            duration_unit = duration_unit.title()
        if duration is not None and duration_unit not in [DAYS, YEARS]:
            raise ValueError(
                "duration unit must be {0} or {1}".format(DAYS, YEARS),
            )
        self._mode = mode
        self._duration = duration
        self._duration_unit = duration_unit

    @property
    def mode(self) -> str | None:
        """Get mode."""
        return self._mode

    @property
    def duration(self) -> tuple[int | None, str | None]:
        """Get duration and it's unit."""
        return self._duration, self._duration_unit

    @classmethod
    def fromxml(cls: Type[A], element: ET.Element) -> A:
        """Create new object with values from XML element."""
        element = find(element, "Rule")
        if element is None:
            return cls(None, None, None)
        element = find(element, "DefaultRetention")
        mode = findtext(element, "Mode")
        duration_unit = DAYS
        duration = findtext(element, duration_unit)
        if not duration:
            duration_unit = YEARS
            duration = findtext(element, duration_unit)
        duration = int(duration)
        return cls(mode, duration, duration_unit)

    def toxml(self, element: ET.Element | None) -> ET.Element:
        """Convert to XML."""
        element = Element("ObjectLockConfiguration")
        SubElement(element, "ObjectLockEnabled", ENABLED)
        if self._mode:
            rule = SubElement(element, "Rule")
            retention = SubElement(rule, "DefaultRetention")
            SubElement(retention, "Mode", self._mode)
            SubElement(retention, self._duration_unit, str(self._duration))
        return element
