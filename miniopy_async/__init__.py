# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage,
# (C) 2015, 2016, 2017 MinIO, Inc.
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

# type: ignore[reportUnusedImport]

"""
miniopy-async - Asynchronous MinIO Client SDK for Python

>>> from miniopy_async import Minio
>>> import asyncio
>>> client = Minio(
...     "play.min.io",
...     access_key="Q3AM3UQ867SPQQA43P2F",
...     secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
...     secure=True  # http for False, https for True
... )
>>> buckets = asyncio.run(
...     client.list_buckets()
... )
>>> for bucket in buckets:
...     print(bucket.name, bucket.creation_date)
"""

__title__ = "miniopy-async"
__author__ = "L-ING"
__version__ = "1.23.2"
__license__ = "Apache 2.0"
__copyright__ = "(C) 2022 L-ING <hlf01@icloud.com>"

from .api import Minio
from .error import InvalidResponseError, S3Error, ServerError
from .minioadmin import MinioAdmin
