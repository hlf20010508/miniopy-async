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
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,
)


async def main():
    # Create bucket.
    print("example one")
    await client.make_bucket("my-bucket1")

    # Create bucket on specific region.
    print("example two")
    await client.make_bucket("my-bucket2", "us-east-1")

    # Create bucket with object-lock feature on specific region.
    print("example three")
    await client.make_bucket("my-bucket3", "us-east-1", object_lock=True)


asyncio.run(main())
