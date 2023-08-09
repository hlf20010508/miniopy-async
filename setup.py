# Asynchronous MinIO Client SDK for Python
# (C) 2015 MinIO, Inc.
# (C) 2022 Huseyn Mashadiyev <mashadiyev.huseyn@gmail.com>
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

import codecs
import re

from setuptools import setup

with codecs.open("miniopy_async/__init__.py") as file:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        file.read(),
        re.MULTILINE,
    ).group(1)

with codecs.open("README.md", encoding="utf-8") as file:
    readme = file.read()

setup(
    name="miniopy-async",
    description="Asynchronous MinIO Client SDK for Python",
    author="L-ING",
    url="https://github.com/hlf20010508/miniopy-async",
    author_email="hlf01@icloud.com",
    version=version,
    long_description_content_type="text/markdown",
    package_dir={"miniopy_async": "miniopy_async"},
    packages=["miniopy_async", "miniopy_async.credentials"],
    install_requires=["certifi", "aiofile", "aiohttp", "urllib3"],
    tests_require=["mock", "nose"],
    license="Apache License 2.0",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    long_description=readme,
    package_data={"": ["LICENSE", "README.md"]},
    include_package_data=True,
    python_requires=">3.6",
)
