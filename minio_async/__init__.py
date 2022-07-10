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

"""
minio-async - Asynchronous MinIO Python SDK

>>> from minio_async import Minio
>>> import asyncio
>>> client = Minio(
...     "play.min.io",
...     access_key="Q3AM3UQ867SPQQA43P2F",
...     secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
...     secure=True  # http for False, https for True
... )
>>> loop = asyncio.get_event_loop()
>>> buckets = loop.run_until_complete(
...     client.list_buckets()
... )
>>> for bucket in buckets:
...     print(bucket.name, bucket.creation_date)
>>> loop.close()

:Copyright © 2022 L-ING.
:license: Apache 2.0, see LICENSE for more details.
"""

__title__ = "miniopy-async"
__author__ = "L-ING."
__version__ = "1.1"
__license__ = "Apache 2.0"
__copyright__ = "Copyright 2022 L-ING"

import threading

__LOCALE_LOCK__ = threading.Lock()

# pylint: disable=unused-import
from .api import Minio
from .error import InvalidResponseError, S3Error, ServerError
from .minioadmin import MinioAdmin
