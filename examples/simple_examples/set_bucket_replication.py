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
from minio_async.commonconfig import DISABLED, ENABLED, AndOperator, Filter
from minio_async.replicationconfig import (DeleteMarkerReplication, Destination, ReplicationConfig, Rule)
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

config = ReplicationConfig(
    "REPLACE-WITH-ACTUAL-ROLE",
    [
        Rule(
            Destination(
                "REPLACE-WITH-ACTUAL-DESTINATION-BUCKET-ARN",
            ),
            ENABLED,
            delete_marker_replication=DeleteMarkerReplication(
                DISABLED,
            ),
            rule_filter=Filter(
                AndOperator(
                    "TaxDocs",
                    {"key1": "value1", "key2": "value2"},
                ),
            ),
            rule_id="rule1",
            priority=1,
        ),
    ],
)

async def main():
    await client.set_bucket_replication("my-bucket", config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
