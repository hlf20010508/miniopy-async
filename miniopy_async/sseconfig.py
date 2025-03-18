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

"""Request/response of PutBucketEncryption and GetBucketEncryption APIs."""

from __future__ import absolute_import, annotations

from abc import ABCMeta
from typing import Type, TypeVar
from xml.etree import ElementTree as ET

from .xml import Element, SubElement, find, findtext

AES256 = "AES256"
AWS_KMS = "aws:kms"

A = TypeVar("A", bound="Rule")


class Rule:
    """Server-side encryption rule."""

    __metaclass__ = ABCMeta

    def __init__(
        self,
        sse_algorithm: str,
        kms_master_key_id: str | None = None,
    ):
        self._sse_algorithm = sse_algorithm
        self._kms_master_key_id = kms_master_key_id

    @property
    def sse_algorithm(self) -> str:
        """Get SSE algorithm."""
        return self._sse_algorithm

    @property
    def kms_master_key_id(self) -> str | None:
        """Get KMS master key ID."""
        return self._kms_master_key_id

    @classmethod
    def new_sse_s3_rule(cls: Type[A]) -> A:
        """Create SSE-S3 rule."""
        return cls(AES256)

    @classmethod
    def new_sse_kms_rule(
        cls: Type[A],
        kms_master_key_id: str | None = None,
    ) -> A:
        """Create new SSE-KMS rule."""
        return cls(AWS_KMS, kms_master_key_id)

    @classmethod
    def fromxml(cls: Type[A], element: ET.Element) -> A:
        """Create new object with values from XML element."""
        element = find(element, "ApplyServerSideEncryptionByDefault")
        sse_algorithm = findtext(element, "SSEAlgorithm", True)
        kms_master_key_id = findtext(element, "KMSMasterKeyID")
        return cls(sse_algorithm, kms_master_key_id)

    def toxml(self, element: ET.Element | None) -> ET.Element:
        """Convert to XML."""
        element = SubElement(element, "Rule")
        tag = SubElement(element, "ApplyServerSideEncryptionByDefault")
        SubElement(tag, "SSEAlgorithm", self._sse_algorithm)
        if self._kms_master_key_id is not None:
            SubElement(tag, "KMSMasterKeyID", self._kms_master_key_id)
        return element


B = TypeVar("B", bound="SSEConfig")


class SSEConfig:
    """server-side encyption configuration."""

    def __init__(self, rule: Rule):
        if not rule:
            raise ValueError("rule must be provided")
        self._rule = rule

    @property
    def rule(self) -> Rule:
        """Get rule."""
        return self._rule

    @classmethod
    def fromxml(cls: Type[B], element: ET.Element) -> B:
        """Create new object with values from XML element."""
        element = find(element, "Rule")
        return cls(Rule.fromxml(element))

    def toxml(self, element: ET.Element | None) -> ET.Element:
        """Convert to XML."""
        element = Element("ServerSideEncryptionConfiguration")
        self._rule.toxml(element)
        return element
