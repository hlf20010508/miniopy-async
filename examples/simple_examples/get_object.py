# -*- coding: utf-8 -*-
# Asynchronous MinIO Python Client API
# (C) 2015 MinIO, Inc.
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

from minio_async import Minio
from minio_async.sse import SseCustomerKey
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    try:
        # Get data of an object.
        print('example one')
        response = await client.get_object("my-bucket", "my-object")
        # Read data from response.

        # Get data of an object from offset and length.
        print('example two')
        response = await client.get_object(
            "my-bucket", "my-object", offset=512, length=1024,
        )
        # Read data from response.

        # Get data of an object of version-ID.
        print('example three')
        response = await client.get_object(
            "my-bucket", "my-object",
            version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
        )
        # Read data from response.

        # Get data of an SSE-C encrypted object.
        print('example four')
        response = await client.get_object(
            "my-bucket", "my-object",
            ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
        )
        # Read data from response.
    finally:
        response.close()
        await response.release()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
