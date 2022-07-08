# Python Client API Reference

## 1. Constructor

### Minio(endpoint, access_key=None, secret_key=None, session_token=None, secure=True, region=None, credentials=None)
Initializes a new client object.

__Parameters__

| Param           | Type                               | Description
|:----------------|:-----------------------------------|:-------------------------------------------------------------------------------|
| `endpoint`      | _str_                              | Hostname of a S3 service.
| `access_key`    | _str_                              | (Optional) Access key (aka user ID) of your account in S3 service.
| `secret_key`    | _str_                              | (Optional) Secret Key (aka password) of your account in S3 service.
| `session_token` | _str_                              | (Optional) Session token of your account in S3 service. 
| `secure`        | _bool_                             | (Optional) Flag to indicate to use secure (TLS) connection to S3 service or not.
| `region`        | _str_                              | (Optional) Region name of buckets in S3 service.                   
| `credentials`   | _minio_async.credentials.Provider_ | (Optional) Credentials provider of your account in S3 service.

__Example__

```py
from minio_async import Minio

# Create client with anonymous access.
client = Minio("play.min.io")

# Create client with access and secret key.
client = Minio("s3.amazonaws.com", "ACCESS-KEY", "SECRET-KEY")

# Create client with access key and secret key with specific region.
client = Minio(
    "play.minio.io:9000",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    region="my-region",
)

# Create client with access key and secret key with http.
client = Minio(
    "play.minio.io:9000",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=False,
)

# Create client with custom HTTP client using proxy server.
import urllib3
client = Minio(
    "SERVER:PORT",
    access_key="ACCESS_KEY",
    secret_key="SECRET_KEY",
    secure=True,
    http_client=urllib3.ProxyManager(
        "https://PROXYSERVER:PROXYPORT/",
        timeout=urllib3.Timeout.DEFAULT_TIMEOUT,
        cert_reqs="CERT_REQUIRED",
        retries=urllib3.Retry(
            total=5,
            backoff_factor=0.2,
            status_forcelist=[500, 502, 503, 504],
        ),
    ),
)
```

| Bucket operations                                           | Object operations                                               |
|:------------------------------------------------------------|:----------------------------------------------------------------|
| [`make_bucket`](#make_bucket)                               | [`get_object`](#get_object)                                     |
| [`list_buckets`](#list_buckets)                             | [`put_object`](#put_object)                                     |
| [`bucket_exists`](#bucket_exists)                           | [`copy_object`](#copy_object)                                   |
| [`remove_bucket`](#remove_bucket)                           | [`compose_object`](#compose_object)                             |
| [`list_objects`](#list_objects)                             | [`stat_object`](#stat_object)                                   |
| [`get_bucket_versioning`](#get_bucket_versioning)           | [`remove_object`](#remove_object)                               |
| [`set_bucket_versioning`](#set_bucket_versioning)           | [`remove_objects`](#remove_objects)                             |
| [`delete_bucket_replication`](#delete_bucket_replication)   | [`fput_object`](#fput_object)                                   |
| [`get_bucket_replication`](#get_bucket_replication)         | [`fget_object`](#fget_object)                                   |
| [`set_bucket_replication`](#set_bucket_replication)         | [`select_object_content`](#select_object_content)               |
| [`delete_bucket_lifecycle`](#delete_bucket_lifecycle)       | [`delete_object_tags`](#delete_object_tags)                     |
| [`get_bucket_lifecycle`](#get_bucket_lifecycle)             | [`get_object_tags`](#get_object_tags)                           |
| [`set_bucket_lifecycle`](#set_bucket_lifecycle)             | [`set_object_tags`](#set_object_tags)                           |
| [`delete_bucket_tags`](#delete_bucket_tags)                 | [`enable_object_legal_hold`](#enable_object_legal_hold)         |
| [`get_bucket_tags`](#get_bucket_tags)                       | [`disable_object_legal_hold`](#disable_object_legal_hold)       |
| [`set_bucket_tags`](#set_bucket_tags)                       | [`is_object_legal_hold_enabled`](#is_object_legal_hold_enabled) |
| [`delete_bucket_policy`](#delete_bucket_policy)             | [`get_object_retention`](#get_object_retention)                 |
| [`get_bucket_policy`](#get_bucket_policy)                   | [`set_object_retention`](#set_object_retention)                 |
| [`set_bucket_policy`](#set_bucket_policy)                   | [`presigned_get_object`](#presigned_get_object)                 |
| [`delete_bucket_notification`](#delete_bucket_notification) | [`presigned_put_object`](#presigned_put_object)                 |
| [`get_bucket_notification`](#get_bucket_notification)       | [`presigned_post_policy`](#presigned_post_policy)               |
| [`set_bucket_notification`](#set_bucket_notification)       | [`get_presigned_url`](#get_presigned_url)                       |
| [`listen_bucket_notification`](#listen_bucket_notification) |                                                                 |
| [`delete_bucket_encryption`](#delete_bucket_encryption)     |                                                                 |
| [`get_bucket_encryption`](#get_bucket_encryption)           |                                                                 |
| [`set_bucket_encryption`](#set_bucket_encryption)           |                                                                 |
| [`delete_object_lock_config`](#delete_object_lock_config)   |                                                                 |
| [`get_object_lock_config`](#get_object_lock_config)         |                                                                 |
| [`set_object_lock_config`](#set_object_lock_config)         |                                                                 |

## 2. Bucket operations

<a id="bucket_exists"></a>

### bucket_exists(bucket_name)

Check if a bucket exists.

__Parameters__

| Param         | Type  | Description         |
|:--------------|:------|:--------------------|
| `bucket_name` | _str_ | Name of the bucket. |

__Example__
```py
from minio_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True
)

res = asyncio.run(
    client.bucket_exists("my-bucket")
)
if res:
    print("my-bucket exists")
else:
    print("my-bucket does not exist")
```