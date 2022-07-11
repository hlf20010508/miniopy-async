# -*- coding: utf-8 -*-
# Asynchronous MinIO Python Client API
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
from miniopy_async.credentials import AssumeRoleProvider
import asyncio

# STS endpoint usually point to MinIO server.
sts_endpoint = "http://STS-HOST:STS-PORT/"

# Access key to fetch credentials from STS endpoint.
access_key = "YOUR-ACCESSKEY"

# Secret key to fetch credentials from STS endpoint.
secret_key = "YOUR-SECRETACCESSKEY"

# Role ARN if available.
role_arn = "ROLE-ARN"

# Role session name if available.
role_session_name = "ROLE-SESSION-NAME"

# External ID if available.
external_id = "EXTERNAL-ID"

# Policy if available.
policy = "POLICY"

# Region if available.
region = "REGION"

provider = AssumeRoleProvider(
    sts_endpoint,
    access_key,
    secret_key,
    policy=policy,
    region=region,
    role_arn=role_arn,
    role_session_name=role_session_name,
    external_id=external_id,
)

client = Minio("MINIO-HOST:MINIO-PORT", secure = False, credentials=provider)

async def main():
    # Get information of an object.
    stat = await client.stat_object("my-bucket", "my-object")
    print(stat)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
