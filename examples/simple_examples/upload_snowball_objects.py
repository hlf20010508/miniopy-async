# -*- coding: utf-8 -*-
# miniopy-async
# (C) 2023 L-ING <hlf01@icloud.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from miniopy_async import Minio
from miniopy_async.commonconfig import SnowballObject
import io
from datetime import datetime
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,  # http for False, https for True
)


async def main():
    await client.upload_snowball_objects(
        "my-bucket",
        [
            SnowballObject("my-object1", filename="LICENSE"),
            SnowballObject(
                "my-object2",
                data=io.BytesIO(b"hello"),
                length=5,
            ),
            SnowballObject(
                "my-object3",
                data=io.BytesIO(b"world"),
                length=5,
                mod_time=datetime.now(),
            ),
        ],
    )


asyncio.run(main())
