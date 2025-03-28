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

from datetime import timedelta
from miniopy_async import Minio
import asyncio


async def main():
    client = Minio(
        "play.min.io",
        access_key="Q3AM3UQ867SPQQA43P2F",
        secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
        secure=True,  # http for False, https for True
    )
    # Get presigned URL string to delete 'my-object' in
    # 'my-bucket' with one day expiry.
    print("example one")
    url = await client.get_presigned_url(
        "DELETE",
        "my-bucket",
        "my-object",
        expires=timedelta(days=1),
    )
    print("url:", url)

    # Get presigned URL string to upload 'my-object' in
    # 'my-bucket' with response-content-type as application/json
    # and one day expiry.
    print("example two")
    url = await client.get_presigned_url(
        "PUT",
        "my-bucket",
        "my-object",
        expires=timedelta(days=1),
        response_headers={"response-content-type": "application/json"},
    )
    print("url:", url)

    # Get presigned URL string to download 'my-object' in
    # 'my-bucket' with two hours expiry.
    print("example three")
    url = await client.get_presigned_url(
        "GET",
        "my-bucket",
        "my-object",
        expires=timedelta(hours=2),
    )
    print("url:", url)

    # Get presigned URL string to download 'my-object' in
    # 'my-bucket' with public IP address when using private IP address.
    client = Minio(
        "127.0.0.1:9000",
        access_key="your access key",
        secret_key="you secret key",
        secure=False,  # http for False, https for True
    )

    print("example four")
    url = await client.get_presigned_url(
        "GET",
        "my-bucket",
        "my-object",
        change_host="https://YOURHOST:YOURPORT",
    )
    print("url:", url)


asyncio.run(main())
