# -*- coding: utf-8 -*-
# Asynchronous MinIO Python SDK
# (C) 2022 L-ING <hlf01@icloud.com>
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

import os
import minio_async

os.system('python setup.py sdist')
os.system('twine upload dist/miniopy-async-%s.tar.gz' %
          minio_async.__version__)
for file in os.listdir('minio_async.egg-info'):
    os.remove(os.path.join('minio_async.egg-info', file))
os.rmdir('minio_async.egg-info')
for file in os.listdir('dist'):
    os.remove(os.path.join('dist', file))
os.rmdir('dist')
