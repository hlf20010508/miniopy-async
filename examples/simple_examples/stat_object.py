# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
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

from miniopy_async import Minio
from miniopy_async.sse import SseCustomerKey
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,  # http for False, https for True
)


async def main():
    # Get object information.
    print("example one")
    result = await client.stat_object("my-bucket", "my-object")
    print(
        "status: last-modified: {0}, size: {1}".format(
            result.last_modified,
            result.size,
        ),
    )

    # Get object information of version-ID.
    print("example two")
    result = await client.stat_object(
        "my-bucket",
        "my-object",
        version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
    )
    print(
        "status: last-modified: {0}, size: {1}".format(
            result.last_modified,
            result.size,
        ),
    )

    # Get SSE-C encrypted object information.
    print("example three")
    result = await client.stat_object(
        "my-bucket",
        "my-object",
        ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
    )
    print(
        "status: last-modified: {0}, size: {1}".format(
            result.last_modified,
            result.size,
        ),
    )


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
