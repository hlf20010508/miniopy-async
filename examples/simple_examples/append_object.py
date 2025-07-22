# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage,
# (C) 2025 MinIO, Inc.
# (C) 2025 L-ING <hlf01@icloud.com>
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

import asyncio
import io
from urllib.request import urlopen

from miniopy_async import Minio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,  # http for False, https for True
)


async def main():
    # Upload data.
    result = await client.put_object(
        "my-bucket",
        "my-object",
        io.BytesIO(b"hello, "),
        7,
    )
    print(f"created {result.object_name} object; etag: {result.etag}")

    # Append data.
    result = await client.append_object(
        "my-bucket",
        "my-object",
        io.BytesIO(b"world"),
        5,
    )
    print(f"appended {result.object_name} object; etag: {result.etag}")

    # Append data in chunks.
    data = urlopen(
        "https://www.kernel.org/pub/linux/kernel/v6.x/linux-6.13.12.tar.xz",
    )
    result = await client.append_object(
        "my-bucket",
        "my-object",
        data,
        148611164,
        5 * 1024 * 1024,
    )
    print(f"appended {result.object_name} object; etag: {result.etag}")

    # Append unknown sized data.
    data = urlopen(
        "https://www.kernel.org/pub/linux/kernel/v6.x/linux-6.14.3.tar.xz",
    )
    result = await client.append_object(
        "my-bucket",
        "my-object",
        data,
        149426584,
        5 * 1024 * 1024,
    )
    print(f"appended {result.object_name} object; etag: {result.etag}")


asyncio.run(main())
