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

import io
from datetime import datetime, timedelta
from urllib.request import urlopen
from minio_async import Minio
from minio_async.commonconfig import GOVERNANCE, Tags
from minio_async.retention import Retention
from minio_async.sse import SseCustomerKey, SseKMS, SseS3
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # Upload data.
    print('example one')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload unknown sized data.
    print('example two')
    data = urlopen(
        "https://raw.githubusercontent.com/hlf20010508/minio-async/master/README.md",
    )
    result = await client.put_object(
        "my-bucket", "my-object", data, length=-1, part_size=10*1024*1024,
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with content-type.
    print('example three')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        content_type="application/csv",
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with metadata.
    print('example four')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        metadata={"Content-Type": "application/octet-stream"},
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with customer key type of server-side encryption.
    print('example five')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with KMS type of server-side encryption.
    print('example six')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        sse=SseKMS("KMS-KEY-ID", {"Key1": "Value1", "Key2": "Value2"}),
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with S3 type of server-side encryption.
    print('example seven')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        sse=SseS3(),
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with tags, retention and legal-hold.
    print('example eight')
    date = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0,
    ) + timedelta(days=30)
    tags = Tags(for_object=True)
    tags["User"] = "jsmith"
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        tags=tags,
        retention=Retention(GOVERNANCE, date),
        legal_hold=True,
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
