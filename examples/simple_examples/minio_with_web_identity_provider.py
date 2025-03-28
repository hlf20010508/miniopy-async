# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
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

import json
import urllib3
from miniopy_async import Minio
from miniopy_async.credentials import WebIdentityProvider
import asyncio


def get_jwt(client_id, client_secret, idp_client_id, idp_endpoint):
    res = urllib3.PoolManager().request(
        "POST",
        idp_endpoint,
        fields={
            "username": client_id,
            "password": client_secret,
            "grant_type": "password",
            "client_id": idp_client_id,
        },
    )

    return json.loads(res.data.encode())


# IDP endpoint.
idp_endpoint = (
    "https://IDP-HOST:IDP-PORT/auth/realms/master" "/protocol/openid-connect/token"
)

# Client-ID to fetch JWT.
client_id = "USER-ID"

# Client secret to fetch JWT.
client_secret = "PASSWORD"

# Client-ID of MinIO service on IDP.
idp_client_id = "MINIO-CLIENT-ID"

# STS endpoint usually point to MinIO server.
sts_endpoint = "http://STS-HOST:STS-PORT/"

# Role ARN if available.
role_arn = "ROLE-ARN"

# Role session name if available.
role_session_name = "ROLE-SESSION-NAME"

provider = WebIdentityProvider(
    lambda: get_jwt(client_id, client_secret, idp_client_id, idp_endpoint),
    sts_endpoint,
    role_arn=role_arn,
    role_session_name=role_session_name,
)

client = Minio("MINIO-HOST:MINIO-PORT", credentials=provider)


async def main():
    # Get information of an object.
    stat = await client.stat_object("my-bucket", "my-object")
    print(stat)


asyncio.run(main())
