# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage,
# (C) 2020 MinIO, Inc.
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

from minio_async import Minio
from minio_async.credentials import IamAwsProvider
import asyncio

client = Minio("s3.amazonaws.com", credentials=IamAwsProvider())

async def main():
    # Get information of an object.
    stat = await client.stat_object("my-bucket", "my-object")
    print(stat)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()

