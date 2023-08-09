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

# NOTICE: This file has been changed and differs from the original
# Author: L-ING
# Date: 2022-07-11

"""Credential module."""

# pylint: disable=unused-import
from .credentials import Credentials
from .providers import (
    AssumeRoleProvider,
    AWSConfigProvider,
    ChainedProvider,
    ClientGrantsProvider,
    EnvAWSProvider,
    EnvMinioProvider,
    IamAwsProvider,
    LdapIdentityProvider,
    MinioClientConfigProvider,
    Provider,
    StaticProvider,
    WebIdentityProvider,
    CertificateIdentityProvider,
)
