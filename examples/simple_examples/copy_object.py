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

from datetime import datetime, timezone
from minio_async import Minio
from minio_async.commonconfig import REPLACE, CopySource
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

loop = asyncio.get_event_loop()

# copy an object from a bucket to another.
print("example one")
result = loop.run_until_complete(
    client.copy_object(
        "my-job-bucket",
        "my-copied-object1",
        CopySource("my-bucket", "my-object"),
    )
)
print(result.object_name, result.version_id)

# copy an object with condition.
print("example two")
result = loop.run_until_complete(
    client.copy_object(
        "my-job-bucket",
        "my-copied-object2",
        CopySource(
            "my-bucket",
            "my-object",
            modified_since=datetime(2014, 4, 1, tzinfo=timezone.utc),
        ),
    )
)
print(result.object_name, result.version_id)

# copy an object from a bucket with replacing metadata.
print("example three")
metadata = {"Content-Type": "application/octet-stream"}
result = loop.run_until_complete(
    client.copy_object(
        "my-job-bucket",
        "my-copied-object3",
        CopySource("my-bucket", "my-object"),
        metadata=metadata,
        metadata_directive=REPLACE,
    )
)
print(result.object_name, result.version_id)

loop.close()