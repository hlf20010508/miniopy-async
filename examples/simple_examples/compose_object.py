# -*- coding: utf-8 -*-
# Asynchronous MinIO Python SDK
# Copyright © 2022 L-ING.
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

from minio_async import Minio
from minio_async.commonconfig import ComposeSource
from minio_async.sse import SseS3
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

# Each part must larger than 5MB
sources = [
    ComposeSource("my-job-bucket", "my-object-part-one"),
    ComposeSource("my-job-bucket", "my-object-part-two"),
    ComposeSource("my-job-bucket", "my-object-part-three"),
]

async def main():
    # Create my-bucket/my-object by combining source object
    # list.
    print('example one')
    result = await client.compose_object("my-bucket", "my-object", sources)
    print(result.object_name, result.version_id)

    # Create my-bucket/my-object with user metadata by combining
    # source object list.
    print('example two')
    result = await client.compose_object(
        "my-bucket",
        "my-object",
        sources,
        metadata={"Content-Type": "application/octet-stream"},
    )
    print(result.object_name, result.version_id)

    # Create my-bucket/my-object with user metadata and
    # server-side encryption by combining source object list.
    print('example three')
    result = await client.compose_object(
        "my-bucket",
        "my-object",
        sources,
        sse=SseS3()
    )
    print(result.object_name, result.version_id)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
