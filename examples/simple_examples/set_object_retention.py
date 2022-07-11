# -*- coding: utf-8 -*-
# Asynchronous MinIO Python API
# Copyright (C) 2020 MinIO, Inc.
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
from minio_async.commonconfig import GOVERNANCE
from minio_async.retention import Retention
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

config = Retention(GOVERNANCE, datetime.utcnow() + timedelta(days=10))

async def main():
    await client.set_object_retention("my-bucket", "my-object", config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
