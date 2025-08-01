# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage,
# (C) 2020 MinIO, Inc.
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

"""Credential providers."""

from __future__ import annotations

import configparser
import ipaddress
import json
import os
import socket
import ssl
import sys
import time
from abc import ABCMeta, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import Awaitable, Callable, cast
from urllib.parse import urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

import certifi
from aiohttp import ClientResponse, ClientSession, TCPConnector
from aiohttp.typedefs import LooseHeaders
from aiohttp_retry import ExponentialRetry, RetryClient
from yarl import URL

from miniopy_async.helpers import sha256_hash, url_replace
from miniopy_async.signer import sign_v4_sts
from miniopy_async.time import from_iso8601utc, to_amz_date, utcnow
from miniopy_async.xml import find, findtext

from .credentials import Credentials

_MIN_DURATION_SECONDS = int(timedelta(minutes=15).total_seconds())
_MAX_DURATION_SECONDS = int(timedelta(days=7).total_seconds())
_DEFAULT_DURATION_SECONDS = int(timedelta(hours=1).total_seconds())


def _parse_credentials(data: str, name: str) -> Credentials:
    """Parse data containing credentials XML."""
    element = ET.fromstring(data)
    element = cast(ET.Element, find(element, name, True))
    element = cast(ET.Element, find(element, "Credentials", True))
    expiration = from_iso8601utc(findtext(element, "Expiration", True))
    return Credentials(
        cast(str, findtext(element, "AccessKeyId", True)),
        cast(str, findtext(element, "SecretAccessKey", True)),
        findtext(element, "SessionToken", True),
        expiration,
    )


def _user_home_dir() -> str:
    """Return current user home folder."""
    return os.environ.get("HOME") or os.environ.get("UserProfile") or str(Path.home())


class Provider:  # pylint: disable=too-few-public-methods
    """Credential retriever."""

    __metaclass__ = ABCMeta
    _session: ClientSession | RetryClient | None = None

    @abstractmethod
    async def retrieve(self) -> Credentials:
        """Retrieve credentials and its expiry if available."""

    def _ensure_session(self):
        raise NotImplementedError

    async def _urlopen(
        self,
        method: str,
        url: str,
        body: str | bytes | None = None,
        headers: LooseHeaders | None = None,
    ) -> ClientResponse:
        """Wrapper of urlopen() handles HTTP status code."""
        self._ensure_session()
        if self._session is None:
            raise ValueError("Session is not initialized")
        session = cast(ClientSession | RetryClient, self._session)
        res = await session.request(method, url, data=body, headers=headers)
        if res.status not in [200, 204, 206]:
            raise ValueError(f"{url} failed with HTTP status code {res.status}")
        return res


class AssumeRoleProvider(Provider):
    """Assume-role credential provider."""

    def __init__(
        self,
        sts_endpoint: str,
        access_key: str,
        secret_key: str,
        duration_seconds: int = 0,
        policy: str | None = None,
        region: str | None = None,
        role_arn: str | None = None,
        role_session_name: str | None = None,
        external_id: str | None = None,
        session: ClientSession | RetryClient | None = None,
    ):
        self._sts_endpoint = sts_endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region or ""
        self._session = session

        query_params = {
            "Action": "AssumeRole",
            "Version": "2011-06-15",
            "DurationSeconds": str(
                duration_seconds
                if duration_seconds > _DEFAULT_DURATION_SECONDS
                else _DEFAULT_DURATION_SECONDS
            ),
        }

        if role_arn:
            query_params["RoleArn"] = role_arn
        if role_session_name:
            query_params["RoleSessionName"] = role_session_name
        if policy:
            query_params["Policy"] = policy
        if external_id:
            query_params["ExternalId"] = external_id

        self._body = urlencode(query_params)
        self._content_sha256 = sha256_hash(self._body)
        url = urlsplit(sts_endpoint)
        self._url = url
        self._host = url.netloc
        if (url.scheme == "http" and url.port == 80) or (
            url.scheme == "https" and url.port == 443
        ):
            self._host = cast(str, url.hostname)
        self._credentials = None

    def _ensure_session(self):
        if self._session is None:
            self._session = RetryClient(
                retry_options=ExponentialRetry(
                    attempts=5, factor=0.2, statuses={500, 502, 503, 504}
                ),
            )

    async def retrieve(self) -> Credentials:
        """Retrieve credentials."""
        if self._credentials and not self._credentials.is_expired():
            return self._credentials

        utctime = utcnow()
        headers = sign_v4_sts(
            "POST",
            self._url,
            self._region,
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": self._host,
                "X-Amz-Date": to_amz_date(utctime),
            },
            Credentials(self._access_key, self._secret_key),
            self._content_sha256,
            utctime,
        )

        res = await self._urlopen(
            "POST",
            self._sts_endpoint,
            body=self._body,
            headers=headers,
        )

        self._credentials = _parse_credentials(
            await res.text(),
            "AssumeRoleResult",
        )

        return self._credentials


class ChainedProvider(Provider):
    """Chained credential provider."""

    def __init__(self, providers: list[Provider]):
        self._providers = providers
        self._provider: Provider | None = None
        self._credentials: Credentials | None = None

    async def retrieve(self) -> Credentials:
        """Retrieve credentials from one of available provider."""
        if self._credentials and not self._credentials.is_expired():
            return self._credentials

        if self._provider:
            try:
                self._credentials = await self._provider.retrieve()
                return self._credentials
            except ValueError:
                # Ignore this error and iterate other providers.
                pass

        for provider in self._providers:
            try:
                self._credentials = await provider.retrieve()
                self._provider = provider
                return self._credentials
            except ValueError:
                # Ignore this error and iterate other providers.
                pass

        raise ValueError("All providers fail to fetch credentials")


class EnvAWSProvider(Provider):
    """Credential provider from AWS environment variables."""

    async def retrieve(self) -> Credentials:
        """Retrieve credentials."""
        return Credentials(
            access_key=(
                cast(
                    str,
                    os.environ.get("AWS_ACCESS_KEY_ID")
                    or os.environ.get("AWS_ACCESS_KEY"),
                )
            ),
            secret_key=(
                cast(
                    str,
                    os.environ.get("AWS_SECRET_ACCESS_KEY")
                    or os.environ.get("AWS_SECRET_KEY"),
                )
            ),
            session_token=os.environ.get("AWS_SESSION_TOKEN"),
        )


class EnvMinioProvider(Provider):
    """Credential provider from MinIO environment variables."""

    async def retrieve(self) -> Credentials:
        """Retrieve credentials."""
        return Credentials(
            access_key=os.environ.get("MINIO_ACCESS_KEY") or "",
            secret_key=os.environ.get("MINIO_SECRET_KEY") or "",
        )


class AWSConfigProvider(Provider):
    """Credential provider from AWS credential file."""

    def __init__(
        self,
        filename: str | None = None,
        profile: str | None = None,
    ):
        self._filename = (
            filename
            or os.environ.get("AWS_SHARED_CREDENTIALS_FILE")
            or os.path.join(_user_home_dir(), ".aws", "credentials")
        )
        self._profile = profile or os.environ.get("AWS_PROFILE") or "default"

    async def retrieve(self) -> Credentials:
        """Retrieve credentials from AWS configuration file."""
        parser = configparser.ConfigParser()
        parser.read(self._filename)
        access_key = parser.get(
            self._profile,
            "aws_access_key_id",
            fallback=None,
        )
        secret_key = parser.get(
            self._profile,
            "aws_secret_access_key",
            fallback=None,
        )
        session_token = parser.get(
            self._profile,
            "aws_session_token",
            fallback=None,
        )

        if not access_key:
            raise ValueError(
                f"access key does not exist in profile "
                f"{self._profile} in AWS credential file {self._filename}"
            )

        if not secret_key:
            raise ValueError(
                f"secret key does not exist in profile "
                f"{self._profile} in AWS credential file {self._filename}"
            )

        return Credentials(
            access_key,
            secret_key,
            session_token=session_token,
        )


class MinioClientConfigProvider(Provider):
    """Credential provider from MinIO Client configuration file."""

    def __init__(self, filename: str | None = None, alias: str | None = None):
        self._filename = filename or os.path.join(
            _user_home_dir(),
            "mc" if sys.platform == "win32" else ".mc",
            "config.json",
        )
        self._alias = alias or os.environ.get("MINIO_ALIAS") or "s3"

    async def retrieve(self) -> Credentials:
        """Retrieve credential value from MinIO client configuration file."""
        try:
            with open(self._filename, encoding="utf-8") as conf_file:
                config = json.loads(conf_file.read())
            aliases = config.get("hosts") or config.get("aliases")
            if not aliases:
                raise ValueError(
                    f"invalid configuration in file {self._filename}",
                )
            creds = aliases.get(self._alias)
            if not creds:
                raise ValueError(
                    f"alias {self._alias} not found in MinIO client"
                    f"configuration file {self._filename}"
                )
            return Credentials(creds.get("accessKey"), creds.get("secretKey"))
        except (IOError, OSError) as exc:
            raise ValueError(
                f"error in reading file {self._filename}",
            ) from exc


def _check_loopback_host(url: str):
    """Check whether host in url points only to localhost."""
    host = cast(str, URL(url).host)
    try:
        addrs = set(info[4][0] for info in socket.getaddrinfo(host, None))
        for addr in addrs:
            if not ipaddress.ip_address(addr).is_loopback:
                raise ValueError(host + " is not loopback only host")
    except socket.gaierror as exc:
        raise ValueError("Host " + host + " is not loopback address") from exc


async def _get_jwt_token(token_file: str) -> dict[str, str]:
    """Read and return content of token file."""
    try:
        with open(token_file, encoding="utf-8") as file:
            return {"access_token": file.read(), "expires_in": "0"}
    except (IOError, OSError) as exc:
        raise ValueError(f"error in reading file {token_file}") from exc


class IamAwsProvider(Provider):
    """Credential provider using IAM roles for Amazon EC2/ECS."""

    def __init__(
        self,
        custom_endpoint: str | None = None,
        session: ClientSession | RetryClient | None = None,
        auth_token: str | None = None,
        relative_uri: str | None = None,
        full_uri: str | None = None,
        token_file: str | None = None,
        role_arn: str | None = None,
        role_session_name: str | None = None,
        region: str | None = None,
    ):
        self._custom_endpoint = custom_endpoint
        self._session = session
        self._token = os.environ.get("AWS_CONTAINER_AUTHORIZATION_TOKEN") or auth_token
        self._token_file = (
            os.environ.get("AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE") or auth_token
        )
        self._identity_file = (
            os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE") or token_file
        )
        self._aws_region = os.environ.get("AWS_REGION") or region
        self._role_arn = os.environ.get("AWS_ROLE_ARN") or role_arn
        self._role_session_name = (
            os.environ.get("AWS_ROLE_SESSION_NAME") or role_session_name
        )
        self._relative_uri = (
            os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI") or relative_uri
        )
        if self._relative_uri and not self._relative_uri.startswith("/"):
            self._relative_uri = "/" + self._relative_uri
        self._full_uri = (
            os.environ.get("AWS_CONTAINER_CREDENTIALS_FULL_URI") or full_uri
        )
        self._credentials: Credentials | None = None

    def _ensure_session(self):
        if self._session is None:
            self._session = RetryClient(
                retry_options=ExponentialRetry(
                    attempts=5, factor=0.2, statuses={500, 502, 503, 504}
                ),
            )

    async def fetch(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> Credentials:
        """Fetch credentials from EC2/ECS."""
        res = await self._urlopen("GET", url, headers=headers)
        data = json.loads(await res.text())
        if data.get("Code", "Success") != "Success":
            raise ValueError(
                f"{url} failed with code {data['Code']} "
                f"message {data.get('Message')}"
            )
        data["Expiration"] = from_iso8601utc(data["Expiration"])

        return Credentials(
            data["AccessKeyId"],
            data["SecretAccessKey"],
            data["Token"],
            data["Expiration"],
        )

    async def retrieve(self) -> Credentials:
        """Retrieve credentials from WebIdentity/EC2/ECS."""

        if self._credentials and not self._credentials.is_expired():
            return self._credentials

        url = self._custom_endpoint
        if self._token_file:
            if not url:
                url = "https://sts.amazonaws.com"
                if self._aws_region:
                    url = f"https://sts.{self._aws_region}.amazonaws.com"

            provider = WebIdentityProvider(
                lambda: _get_jwt_token(cast(str, self._identity_file)),
                url,
                role_arn=self._role_arn,
                role_session_name=self._role_session_name,
                session=self._session,
            )
            self._credentials = await provider.retrieve()
            return self._credentials

        headers: dict[str, str] | None = None
        if self._relative_uri:
            if not url:
                url = "http://169.254.170.2" + self._relative_uri
            headers = {"Authorization": self._token} if self._token else None
        elif self._full_uri:
            token = self._token
            if self._token_file:
                url = self._full_uri
                with open(self._token_file, encoding="utf-8") as file:
                    token = file.read()
            else:
                if not url:
                    url = self._full_uri
                    _check_loopback_host(url)
            headers = {"Authorization": token} if token else None
        else:
            if not url:
                url = "http://169.254.169.254"

            # Get IMDS Token
            res = await self._urlopen(
                "PUT",
                url + "/latest/api/token",
                headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            )
            token = await res.text("utf-8")
            headers = {"X-aws-ec2-metadata-token": token} if token else None

            # Get role name
            url = urlunsplit(
                url_replace(
                    urlsplit(url),
                    path="/latest/meta-data/iam/security-credentials/",
                ),
            )
            res = await self._urlopen("GET", url, headers=headers)
            role_names = (await res.text("utf-8")).split("\n")
            if not role_names:
                raise ValueError(f"no IAM roles attached to EC2 service {url}")
            url += role_names[0].strip("\r")
        if not url:
            raise ValueError("url is empty; this should not happen")
        self._credentials = await self.fetch(url, headers=headers)
        return self._credentials


class LdapIdentityProvider(Provider):
    """Credential provider using AssumeRoleWithLDAPIdentity API."""

    def __init__(
        self,
        sts_endpoint: str,
        ldap_username: str,
        ldap_password: str,
        session: ClientSession | RetryClient | None = None,
    ):
        self._sts_endpoint = (
            sts_endpoint
            + "?"
            + urlencode(
                {
                    "Action": "AssumeRoleWithLDAPIdentity",
                    "Version": "2011-06-15",
                    "LDAPUsername": ldap_username,
                    "LDAPPassword": ldap_password,
                },
            )
        )
        self._session = session
        self._credentials = None

    def _ensure_session(self):
        if self._session is None:
            self._session = RetryClient(
                retry_options=ExponentialRetry(
                    attempts=5, factor=0.2, statuses={500, 502, 503, 504}
                ),
            )

    async def retrieve(self) -> Credentials:
        """Retrieve credentials."""

        if self._credentials and not self._credentials.is_expired():
            return self._credentials

        res = await self._urlopen(
            "POST",
            self._sts_endpoint,
        )

        self._credentials = _parse_credentials(
            await res.text(),
            "AssumeRoleWithLDAPIdentityResult",
        )

        return self._credentials


class StaticProvider(Provider):
    """Fixed credential provider."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        session_token: str | None = None,
    ):
        self._credentials = Credentials(access_key, secret_key, session_token)

    async def retrieve(self) -> Credentials:
        """Return passed credentials."""
        return self._credentials


class WebIdentityClientGrantsProvider(Provider):
    """Base class for WebIdentity and ClientGrants credentials provider."""

    __metaclass__ = ABCMeta

    def __init__(
        self,
        jwt_provider_func: Callable[[], Awaitable[dict[str, str]]],
        sts_endpoint: str,
        duration_seconds: int = 0,
        policy: str | None = None,
        role_arn: str | None = None,
        role_session_name: str | None = None,
        session: ClientSession | RetryClient | None = None,
    ):
        self._jwt_provider_func = jwt_provider_func
        self._sts_endpoint = sts_endpoint
        self._duration_seconds = duration_seconds
        self._policy = policy
        self._role_arn = role_arn
        self._role_session_name = role_session_name
        self._session = session
        self._credentials: Credentials | None = None

    def _ensure_session(self):
        if self._session is None:
            self._session = RetryClient(
                retry_options=ExponentialRetry(
                    attempts=5, factor=0.2, statuses={500, 502, 503, 504}
                ),
            )

    @abstractmethod
    def _is_web_identity(self) -> bool:
        """Check if derived class deal with WebIdentity."""

    def _get_duration_seconds(self, expiry: int) -> int:
        """Get DurationSeconds optimal value."""

        if self._duration_seconds:
            expiry = self._duration_seconds

        if expiry > _MAX_DURATION_SECONDS:
            return _MAX_DURATION_SECONDS

        if expiry <= 0:
            return expiry

        return _MIN_DURATION_SECONDS if expiry < _MIN_DURATION_SECONDS else expiry

    async def retrieve(self) -> Credentials:
        """Retrieve credentials."""

        if self._credentials and not self._credentials.is_expired():
            return self._credentials

        jwt = await self._jwt_provider_func()

        query_params = {"Version": "2011-06-15"}
        duration_seconds = self._get_duration_seconds(
            int(jwt.get("expires_in", "0")),
        )
        if duration_seconds:
            query_params["DurationSeconds"] = str(duration_seconds)
        if self._policy:
            query_params["Policy"] = self._policy

        access_token = jwt.get("access_token") or jwt.get("id_token", "")
        if self._is_web_identity():
            query_params["Action"] = "AssumeRoleWithWebIdentity"
            query_params["WebIdentityToken"] = access_token
            if self._role_arn:
                query_params["RoleArn"] = self._role_arn
                query_params["RoleSessionName"] = (
                    self._role_session_name
                    if self._role_session_name
                    else str(time.time()).replace(".", "")
                )
        else:
            query_params["Action"] = "AssumeRoleWithClientGrants"
            query_params["Token"] = access_token

        url = self._sts_endpoint + "?" + urlencode(query_params)
        res = await self._urlopen("POST", url)

        self._credentials = _parse_credentials(
            await res.text(),
            (
                "AssumeRoleWithWebIdentityResult"
                if self._is_web_identity()
                else "AssumeRoleWithClientGrantsResult"
            ),
        )

        return self._credentials


class ClientGrantsProvider(WebIdentityClientGrantsProvider):
    """Credential provider using AssumeRoleWithClientGrants API."""

    def __init__(
        self,
        jwt_provider_func: Callable[[], Awaitable[dict[str, str]]],
        sts_endpoint: str,
        duration_seconds: int = 0,
        policy: str | None = None,
        session: ClientSession | RetryClient | None = None,
    ):
        super().__init__(
            jwt_provider_func,
            sts_endpoint,
            duration_seconds,
            policy,
            session=session,
        )

    def _is_web_identity(self) -> bool:
        return False


class WebIdentityProvider(WebIdentityClientGrantsProvider):
    """Credential provider using AssumeRoleWithWebIdentity API."""

    def _is_web_identity(self) -> bool:
        return True


class CertificateIdentityProvider(Provider):
    """Credential provider using AssumeRoleWithCertificate API."""

    def __init__(
        self,
        sts_endpoint: str,
        cert_file: str | None = None,
        key_file: str | None = None,
        key_password: str | None = None,
        ca_certs: str | None = None,
        duration_seconds: int = 0,
        session: ClientSession | RetryClient | None = None,
    ):
        if urlsplit(sts_endpoint).scheme != "https":
            raise ValueError("STS endpoint scheme must be HTTPS")

        if bool(session) != (cert_file and key_file):
            pass
        else:
            raise ValueError(
                "either cert/key file or custom session must be provided",
            )

        self._sts_endpoint = (
            sts_endpoint
            + "?"
            + urlencode(
                {
                    "Action": "AssumeRoleWithCertificate",
                    "Version": "2011-06-15",
                    "DurationSeconds": str(
                        duration_seconds
                        if duration_seconds > _DEFAULT_DURATION_SECONDS
                        else _DEFAULT_DURATION_SECONDS
                    ),
                },
            )
        )

        self._ca_certs = ca_certs
        self._cert_file = cert_file
        self._key_file = key_file
        self._key_password = key_password
        self._session = session
        self._credentials: Credentials | None = None

    def _ensure_session(self):
        if self._session is None:
            ssl_context = ssl.create_default_context(
                cafile=self._ca_certs or certifi.where()
            )
            if self._cert_file and self._key_file:
                ssl_context.load_cert_chain(
                    certfile=self._cert_file,
                    keyfile=self._key_file,
                    password=self._key_password,
                )

            retry_options = ExponentialRetry(
                attempts=5, factor=0.2, statuses={500, 502, 503, 504}
            )

            self._session = RetryClient(
                ClientSession(
                    connector=TCPConnector(limit=10, ssl=ssl_context),
                ),
                retry_options=retry_options,
            )

    async def retrieve(self) -> Credentials:
        """Retrieve credentials."""

        if self._credentials and not self._credentials.is_expired():
            return self._credentials

        res = await self._urlopen(
            "POST",
            self._sts_endpoint,
        )

        self._credentials = _parse_credentials(
            await res.text(),
            "AssumeRoleWithCertificateResult",
        )

        return self._credentials
