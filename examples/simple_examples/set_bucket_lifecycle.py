# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
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

from miniopy_async import Minio
from miniopy_async.commonconfig import ENABLED, Filter
from miniopy_async.lifecycleconfig import Expiration, LifecycleConfig, Rule, Transition
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,  # http for False, https for True
)

config = LifecycleConfig(
    [
        Rule(
            ENABLED,
            rule_filter=Filter(prefix="documents/"),
            rule_id="rule1",
            transition=Transition(days=30, storage_class="GLACIER"),
        ),
        Rule(
            ENABLED,
            rule_filter=Filter(prefix="logs/"),
            rule_id="rule2",
            expiration=Expiration(days=365),
        ),
    ],
)


async def main():
    await client.set_bucket_lifecycle("my-bucket", config)


asyncio.run(main())
