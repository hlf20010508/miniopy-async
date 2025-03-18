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
from miniopy_async.deleteobjects import DeleteObject
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,  # http for False, https for True
)


async def main():
    # Remove list of objects.
    print("example one")
    errors = await client.remove_objects(
        "my-bucket",
        [
            DeleteObject("my-object1"),
            DeleteObject("my-object2"),
            DeleteObject("my-object3", "13f88b18-8dcd-4c83-88f2-8631fdb6250c"),
        ],
    )
    async for error in errors:
        print("error occured when deleting object", error)

    # Remove a prefix recursively.
    print("example two")
    delete_object_list = [
        DeleteObject(obj.object_name)
        for obj in await client.list_objects("my-bucket", "my/prefix/", recursive=True)
    ]
    errors = await client.remove_objects("my-bucket", delete_object_list)
    async for error in errors:
        print("error occured when deleting object", error)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
