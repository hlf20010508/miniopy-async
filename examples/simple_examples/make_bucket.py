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
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True
)

loop = asyncio.get_event_loop()

# Create bucket.
print('example one')
loop.run_until_complete(
    client.make_bucket("my-bucket1")
)


# Create bucket on specific region.
print('example two')
loop.run_until_complete(
    client.make_bucket("my-bucket2", "us-east-1")
)

# Create bucket with object-lock feature on specific region.
print('example three')
loop.run_until_complete(
    client.make_bucket("my-bucket3", "us-east-1", object_lock=True)
)

loop.close()