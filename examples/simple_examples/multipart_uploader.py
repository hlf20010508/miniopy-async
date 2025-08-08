# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
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

from miniopy_async import Minio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,  # http for False, https for True
)


async def main():
    # Use context manager
    print("example one")
    async with client.multipart_uploader(
        "my-bucket",
        "my-object",
    ) as uploader:
        await uploader.upload_part(b"hello ", 1)
        await uploader.upload_part(b"world", 2)
    result = uploader.result
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name,
            result.etag,
            result.version_id,
        ),
    )

    # Use directly
    print("example two")
    uploader = client.multipart_uploader(
        "my-bucket",
        "my-object",
    )
    await uploader.upload_part(b"hello ", 1)
    await uploader.upload_part(b"world", 2)
    result = await uploader.complete()
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name,
            result.etag,
            result.version_id,
        ),
    )

    # Abort
    print("example three")
    uploader = client.multipart_uploader(
        "my-bucket",
        "my-object",
    )
    await uploader.upload_part(b"hello ", 1)
    await uploader.abort()

    # Parallel upload
    print("example four")
    tasks = []
    async with client.multipart_uploader(
        "my-bucket",
        "my-object",
    ) as uploader:
        for i in range(1, 11):
            data = f"part {i}".encode("utf-8")
            tasks.append(uploader.upload_part(data, i))
        await asyncio.gather(*tasks)
    result = uploader.result
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name,
            result.etag,
            result.version_id,
        ),
    )


asyncio.run(main())
