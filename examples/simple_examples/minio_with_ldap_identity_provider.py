# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
# (C) 2020 MinIO, Inc.
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

from miniopy_async import Minio
from miniopy_async.credentials import LdapIdentityProvider
import asyncio

# STS endpoint usually point to MinIO server.
sts_endpoint = "http://STS-HOST:STS-PORT/"

# LDAP username.
ldap_username = "LDAP-USERNAME"

# LDAP password.
ldap_password = "LDAP-PASSWORD"

provider = LdapIdentityProvider(sts_endpoint, ldap_username, ldap_password)

client = Minio("MINIO-HOST:MINIO-PORT", credentials=provider)


async def main():
    # Get information of an object.
    stat = await client.stat_object("my-bucket", "my-object")
    print(stat)


asyncio.run(main())
