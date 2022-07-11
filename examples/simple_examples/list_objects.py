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

from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # List objects information.
    print('example one')
    objects = await client.list_objects("my-bucket")
    for obj in objects:
        print('obj:',obj)

    # List objects information whose names starts with "my/prefix/".
    print('example two')
    objects = await client.list_objects("my-bucket", prefix="my/prefix/")
    for obj in objects:
        print('obj:',obj)

    # List objects information recursively.
    print('example three')
    objects = await client.list_objects("my-bucket", recursive=True)
    for obj in objects:
        print('obj:',obj)

    # List objects information recursively whose names starts with
    # "my/prefix/".
    print('example four')
    objects = await client.list_objects(
        "my-bucket", prefix="my/prefix/", recursive=True,
    )
    for obj in objects:
        print('obj:',obj)

    # List objects information recursively after object name
    # "my/prefix/world/1".
    print('example five')
    objects = await client.list_objects(
        "my-bucket", recursive=True, start_after="my/prefix/world/1",
    )
    for obj in objects:
        print('obj:',obj)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
