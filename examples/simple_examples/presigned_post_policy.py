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

from datetime import datetime, timedelta
from minio_async import Minio
from minio_async.datatypes import PostPolicy
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

policy = PostPolicy(
    "my-bucket", datetime.utcnow() + timedelta(days=10),
)
policy.add_starts_with_condition("key", "my/object/prefix/")
policy.add_content_length_range_condition(1*1024*1024, 10*1024*1024)

async def main():
    form_data = await client.presigned_post_policy(policy)
    curl_cmd = (
        "curl -X POST "
        "https://play.min.io/my-bucket "
        "{0} -F file=@<FILE>"
    ).format(
        " ".join(["-F {0}={1}".format(k, v) for k, v in form_data.items()]),
    )
    print('curl_cmd:',curl_cmd)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
