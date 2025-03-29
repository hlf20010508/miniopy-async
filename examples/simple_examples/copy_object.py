# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
# (C) 2016-2020 MinIO, Inc.
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

from datetime import datetime, timezone
from typing import cast
from miniopy_async import Minio
from miniopy_async.commonconfig import REPLACE, CopySource
import asyncio

from miniopy_async.datatypes import DictType

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,  # http for False, https for True
)


async def main():
    # copy an object from a bucket to another.
    print("example one")
    result = await client.copy_object(
        "my-job-bucket",
        "my-copied-object1",
        CopySource("my-bucket", "my-object"),
    )
    print(result.object_name, result.version_id)

    # copy an object with condition.
    print("example two")
    result = await client.copy_object(
        "my-job-bucket",
        "my-copied-object2",
        CopySource(
            "my-bucket",
            "my-object",
            modified_since=datetime(2014, 4, 1, tzinfo=timezone.utc),
        ),
    )
    print(result.object_name, result.version_id)

    # copy an object from a bucket with replacing metadata.
    print("example three")
    metadata = {"Content-Type": "application/octet-stream"}
    result = await client.copy_object(
        "my-job-bucket",
        "my-copied-object3",
        CopySource("my-bucket", "my-object"),
        metadata=cast(DictType, metadata),
        metadata_directive=REPLACE,
    )
    print(result.object_name, result.version_id)


asyncio.run(main())
