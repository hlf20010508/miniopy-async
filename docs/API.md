# Asynchronous MinIO Python Client API Reference

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
| `credentials`   | _miniopy_async.credentials.Provider_ | (Optional) Credentials provider of your account in S3 service.

__Example__

```py
from miniopy_async import Minio

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

<a id="make_bucket"></a>

### make_bucket(bucket_name, location='us-east-1', object_lock=False)

Create a bucket with region and object lock.

__Parameters__

| Param         | Type   | Description                                 |
|---------------|--------|---------------------------------------------|
| `bucket_name` | _str_  | Name of the bucket.                         |
| `location`    | _str_  | Region in which the bucket will be created. |
| `object_lock` | _bool_ | Flag to set object-lock feature.            |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True
)

async def main():
    # Create bucket.
    print('example one')
    await client.make_bucket("my-bucket1")

    # Create bucket on specific region.
    print('example two')
    await client.make_bucket("my-bucket2", "us-east-1")

    # Create bucket with object-lock feature on specific region.
    print('example three')
    await client.make_bucket("my-bucket3", "us-east-1", object_lock=True)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="list_buckets"></a>

### list_buckets()

List information of all accessible buckets.

__Parameters__

| Return           |
|:-----------------|
| List of _Bucket_ |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    buckets = await client.list_buckets()
    for bucket in buckets:
        print(bucket.name, bucket.creation_date)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="bucket_exists"></a>

### bucket_exists(bucket_name)

Check if a bucket exists.

__Parameters__

| Param         | Type  | Description         |
|:--------------|:------|:--------------------|
| `bucket_name` | _str_ | Name of the bucket. |

__Example__
```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    result = await client.bucket_exists("my-bucket")
    if result:
        print("my-bucket exists")
    else:
        print("my-bucket does not exist")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="remove_bucket"></a>

### remove_bucket(bucket_name)

Remove an empty bucket.

__Parameters__

| Param         | Type  | Description         |
|:--------------|:------|:--------------------|
| `bucket_name` | _str_ | Name of the bucket. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.remove_bucket("my-bucket")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="list_objects"></a>

### list_objects(bucket_name, prefix=None, recursive=False, start_after=None, include_user_meta=False, include_version=False, use_api_v1=False, use_url_encoding_type=True)

Lists object information of a bucket.

__Parameters__

| Param                   | Type   | Description                                                  |
|:------------------------|:-------|:-------------------------------------------------------------|
| `bucket_name`           | _str_  | Name of the bucket.                                          |
| `prefix`                | _str_  | Object name starts with prefix.                              |
| `recursive`             | _bool_ | List recursively than directory structure emulation.         |
| `start_after`           | _str_  | List objects after this key name.                            |
| `include_user_meta`     | _bool_ | MinIO specific flag to control to include user metadata.     |
| `include_version`       | _bool_ | Flag to control whether include object versions.             |
| `use_api_v1`            | _bool_ | Flag to control to use ListObjectV1 S3 API or not.           |
| `use_url_encoding_type` | _bool_ | Flag to control whether URL encoding type to be used or not. |

__Return Value__

| Return                  |
|:------------------------|
| An iterator of _Object_ |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # List objects information.
    print('example one')
    objects = await client.list_objects("my-bucket")
    for obj in objects:
        print('obj:',obj)

    # List objects information whose names starts with "my/prefix/".
    print('example two')
    objects = await client.list_objects("my-bucket", prefix="my/prefix/")
    for obj in objects:
        print('obj:',obj)

    # List objects information recursively.
    print('example three')
    objects = await client.list_objects("my-bucket", recursive=True)
    for obj in objects:
        print('obj:',obj)

    # List objects information recursively whose names starts with
    # "my/prefix/".
    print('example four')
    objects = await client.list_objects(
        "my-bucket", prefix="my/prefix/", recursive=True,
    )
    for obj in objects:
        print('obj:',obj)

    # List objects information recursively after object name
    # "my/prefix/world/1".
    print('example five')
    objects = await client.list_objects(
        "my-bucket", recursive=True, start_after="my/prefix/world/1",
    )
    for obj in objects:
        print('obj:',obj)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_bucket_policy"></a>

### get_bucket_policy(bucket_name)

Get bucket policy configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Return Value__

| Param                                       |
|:--------------------------------------------|
| Bucket policy configuration as JSON string. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    policy = await client.get_bucket_policy("my-bucket")
    print(policy)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_bucket_policy"></a>

### set_bucket_policy(bucket_name, policy)

Set bucket policy configuration to a bucket.

__Parameters__

| Param           | Type  | Description                                 |
|:----------------|:------|:--------------------------------------------|
| ``bucket_name`` | _str_ | Name of the bucket.                         |
| ``Policy``      | _str_ | Bucket policy configuration as JSON string. |

__Example__

```py
import json
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # Example anonymous read-only bucket policy.
    print('example one')
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                "Resource": "arn:aws:s3:::my-bucket",
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::my-bucket/*",
            },
        ],
    }
    await client.set_bucket_policy("my-bucket", json.dumps(policy))

    # Example anonymous read-write bucket policy.
    print('example two')
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": [
                    "s3:GetBucketLocation",
                    "s3:ListBucket",
                    "s3:ListBucketMultipartUploads",
                ],
                "Resource": "arn:aws:s3:::my-bucket",
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListMultipartUploadParts",
                    "s3:AbortMultipartUpload",
                ],
                "Resource": "arn:aws:s3:::my-bucket/images/*",
            },
        ],
    }
    await client.set_bucket_policy("my-bucket", json.dumps(policy))

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="delete_bucket_policy"></a>

### delete_bucket_policy(bucket_name)

Delete bucket policy configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.delete_bucket_policy("my-bucket")

loop=asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_bucket_notification"></a>

### get_bucket_notification(bucket_name)

Get notification configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Return Value__

| Param                        |
|:-----------------------------|
| _NotificationConfig_ object. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    config = await client.get_bucket_notification("my-bucket")
    print(config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_bucket_notification"></a>

### set_bucket_notification(bucket_name, config)

Set notification configuration of a bucket.

__Parameters__

| Param           | Type                 | Description                 |
|:----------------|:---------------------|:----------------------------|
| ``bucket_name`` | _str_                | Name of the bucket.         |
| ``config``      | _NotificationConfig_ | Notification configuration. |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.notificationconfig import (NotificationConfig, PrefixFilterRule, QueueConfig)
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

config = NotificationConfig(
    queue_config_list=[
        QueueConfig(
            "QUEUE-ARN-OF-THIS-BUCKET",
            ["s3:ObjectCreated:*"],
            config_id="1",
            prefix_filter_rule=PrefixFilterRule("abc"),
        ),
    ],
)

async def main():
    await client.set_bucket_notification("my-bucket", config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="delete_bucket_notification"></a>

### delete_bucket_notification(bucket_name)

Delete notification configuration of a bucket. On success, S3 service stops notification of events previously set of the bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.delete_bucket_notification("my-bucket")

loop=asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="listen_bucket_notification"></a>

### listen_bucket_notification(bucket_name, prefix='', suffix='', events=('s3:ObjectCreated:\*', 's3:ObjectRemoved:\*', 's3:ObjectAccessed:\*'))

Listen events of object prefix and suffix of a bucket. Caller should iterate returned iterator to read new events.

__Parameters__

| Param         | Type   | Description                                 |
|:--------------|:-------|:--------------------------------------------|
| `bucket_name` | _str_  | Name of the bucket.                         |
| `prefix`      | _str_  | Listen events of object starts with prefix. |
| `suffix`      | _str_  | Listen events of object ends with suffix.   |
| `events`      | _list_ | Events to listen.                           |

__Return Value__

| Param                               |
|:------------------------------------|
| Iterator of event records as _dict_ |

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    events = await client.listen_bucket_notification(
        "my-bucket",
        prefix="my-prefix/",
        events=["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
    )
    async for event in events:
        print('event:',event)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_bucket_encryption"></a>

### get_bucket_encryption(bucket_name)

Get encryption configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Return Value__

| Param               |
|:--------------------|
| _SSEConfig_ object. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    config = await client.get_bucket_encryption("my-bucket")
    print(config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_bucket_encryption"></a>

### set_bucket_encryption(bucket_name, config)

Set encryption configuration of a bucket.

__Parameters__

| Param           | Type        | Description                           |
|:----------------|:------------|:--------------------------------------|
| ``bucket_name`` | _str_       | Name of the bucket.                   |
| ``config``      | _SSEConfig_ | Server-side encryption configuration. |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.sseconfig import Rule, SSEConfig
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.set_bucket_encryption(
        "my-bucket", SSEConfig(Rule.new_sse_s3_rule()),
    )

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="delete_bucket_encryption"></a>

### delete_bucket_encryption(bucket_name)

Delete encryption configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.delete_bucket_encryption("my-bucket")

loop=asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_bucket_versioning"></a>

### get_bucket_versioning(bucket_name)

Get versioning configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    config = await client.get_bucket_versioning("my-bucket")
    print(config.status)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_bucket_versioning"></a>

### set_bucket_versioning(bucket_name, config)

Set versioning configuration to a bucket.

__Parameters__

| Param           | Type               | Description               |
|:----------------|:-------------------|:--------------------------|
| ``bucket_name`` | _str_              | Name of the bucket.       |
| ``config``      | _VersioningConfig_ | Versioning configuration. |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.commonconfig import ENABLED
from miniopy_async.versioningconfig import VersioningConfig
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.set_bucket_versioning("my-bucket", VersioningConfig(ENABLED))

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="delete_bucket_replication"></a>

### delete_bucket_replication(bucket_name)

Delete replication configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.delete_bucket_replication("my-bucket")

loop=asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_bucket_replication"></a>

### get_bucket_replication(bucket_name)

Get replication configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

| Return                                  |
|:----------------------------------------|
| _ReplicationConfig_ object. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    config = await client.get_bucket_replication("my-bucket")
    print(config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_bucket_replication"></a>

### set_bucket_replication(bucket_name, config)

Set replication configuration to a bucket.

__Parameters__

| Param           | Type                | Description                |
|:----------------|:--------------------|:---------------------------|
| ``bucket_name`` | _str_               | Name of the bucket.        |
| ``config``      | _ReplicationConfig_ | Replication configuration. |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.commonconfig import DISABLED, ENABLED, AndOperator, Filter, Tags
from miniopy_async.replicationconfig import (DeleteMarkerReplication, Destination, ReplicationConfig, Rule)
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

bucket_tags = Tags.new_bucket_tags()
bucket_tags["Project"] = "Project One"
bucket_tags["User"] = "jsmith"

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
                    bucket_tags,
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
```

<a id="delete_bucket_lifecycle"></a>

### delete_bucket_lifecycle(bucket_name)

Delete lifecycle configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.delete_bucket_lifecycle("my-bucket")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_bucket_lifecycle"></a>

### get_bucket_lifecycle(bucket_name)

Get lifecycle configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

| Return                    |
|:--------------------------|
| _LifecycleConfig_ object. |


__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    config = await client.get_bucket_lifecycle("my-bucket")
    print(config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_bucket_lifecycle"></a>

### set_bucket_lifecycle(bucket_name, config)

Set lifecycle configuration to a bucket.

__Parameters__

| Param           | Type              | Description              |
|:----------------|:------------------|:-------------------------|
| ``bucket_name`` | _str_             | Name of the bucket.      |
| ``config``      | _LifecycleConfig_ | Lifecycle configuration. |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.commonconfig import ENABLED, Filter
from miniopy_async.lifecycleconfig import Expiration, LifecycleConfig, Rule, Transition
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
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

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="delete_bucket_tags"></a>

### delete_bucket_tags(bucket_name)

Delete tags configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.delete_bucket_tags("my-bucket")

loop=asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_bucket_tags"></a>

### get_bucket_tags(bucket_name)

Get tags configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

| Return         |
|:---------------|
| _Tags_ object. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    tags = await client.get_bucket_tags("my-bucket")
    print(tags)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_bucket_tags"></a>

### set_bucket_tags(bucket_name, tags)

Set tags configuration to a bucket.

__Parameters__

| Param           | Type   | Description         |
|:----------------|:-------|:--------------------|
| ``bucket_name`` | _str_  | Name of the bucket. |
| ``tags``        | _Tags_ | Tags configuration. |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.commonconfig import Tags
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

tags = Tags.new_bucket_tags()
tags["Project"] = "Project One"
tags["User"] = "jsmith"

async def main():
    await client.set_bucket_tags("my-bucket", tags)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="delete_object_lock_config"></a>

### delete_object_lock_config(bucket_name)

Delete object-lock configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.delete_object_lock_config("my-bucket")

loop=asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_object_lock_config"></a>

### get_object_lock_config(bucket_name)

Get object-lock configuration of a bucket.

__Parameters__

| Param           | Type  | Description         |
|:----------------|:------|:--------------------|
| ``bucket_name`` | _str_ | Name of the bucket. |

| Return                     |
|:---------------------------|
| _ObjectLockConfig_ object. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    config = await client.get_object_lock_config("my-bucket")
    print(config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_object_lock_config"></a>

### set_object_lock_config(bucket_name, config)

Set object-lock configuration to a bucket.

__Parameters__

| Param           | Type               | Description                |
|:----------------|:-------------------|:---------------------------|
| ``bucket_name`` | _str_              | Name of the bucket.        |
| ``config``      | _ObjectLockConfig_ | Object-Lock configuration. |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.commonconfig import GOVERNANCE
from miniopy_async.objectlockconfig import DAYS, ObjectLockConfig
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

config = ObjectLockConfig(GOVERNANCE, 15, DAYS)

async def main():
    await client.set_object_lock_config("my-bucket", config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

## 3. Object operations

<a id="get_object"></a>

### get_object(bucket_name, object_name, session, offset=0, length=0, request_headers=None, ssec=None, version_id=None, extra_query_params=None)

Gets data from offset to length of an object. Returned response should be closed after use to release network resources.

__Parameters__

| Param                | Type                    | Description                                          |
|:---------------------|:------------------------|:-----------------------------------------------------|
| `bucket_name`        | _str_                   | Name of the bucket.                                  |
| `object_name`        | _str_                   | Object name in the bucket.                           |
| `session`            | _aiohttp.ClientSession_ | aiohttp.ClientSession object.                        |
| `offset`             | _int_                   | Start byte position of object data.                  |
| `length`             | _int_                   | Number of bytes of object data from offset.          |
| `request_headers`    | _dict_                  | Any additional headers to be added with GET request. |
| `ssec`               | _SseCustomerKey_        | Server-side encryption customer key.                 |
| `version_id`         | _str_                   | Version-ID of the object.                            |
| `extra_query_params` | _dict_                  | Extra query parameters for advanced usage.           |

__Return Value__

| Return                                  |
|:----------------------------------------|
| _aiohttp.client_reqrep.ClientResponse_ object. |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.sse import SseCustomerKey
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # Get data of an object.
    print('example one')
    async with aiohttp.ClientSession() as session:
        response = await client.get_object("my-bucket", "my-object", session)
        # Read data from response.

    # Get data of an object from offset and length.
    print('example two')
    async with aiohttp.ClientSession() as session:
        response = await client.get_object(
            "my-bucket", "my-object", session, offset=512, length=1024,
        )
        # Read data from response.

    # Get data of an object of version-ID.
    print('example three')
    async with aiohttp.ClientSession() as session:
        response = await client.get_object(
            "my-bucket", "my-object", sessioin
            version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
        )
        # Read data from response.

    # Get data of an SSE-C encrypted object.
    print('example four')
    async with aiohttp.ClientSession() as session:
        response = await client.get_object(
            "my-bucket", "my-object", session
            ssec=SseCustomerKey(
            b"32byteslongsecretkeymustprovided"),
        )
        # Read data from response.

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="select_object_content"></a>

### select_object_content(bucket_name, object_name, request)

Select content of an object by SQL expression.

__Parameters__

| Param         | Type            | Description                |
|:--------------|:----------------|:---------------------------|
| `bucket_name` | _str_           | Name of the bucket.        |
| `object_name` | _str_           | Object name in the bucket. |
| `request`     | _SelectRequest_ | Select request.            |

__Return Value__

| Return                                                                               |
|:-------------------------------------------------------------------------------------|
| A reader contains requested records and progress information as _async_generator_ object |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.select import (CSVInputSerialization, CSVOutputSerialization, SelectRequest)
from aiostream.stream import list as alist
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    result = await client.select_object_content(
        "my-bucket",
        "my-object.csv",
        SelectRequest(
            "select * from s3object",
            CSVInputSerialization(),
            CSVOutputSerialization(),
            request_progress=True,
        ),
    )
    print('data:')
    for data in await alist(result.stream()):
        print(data.decode())
    print('status:',result.stats())

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="fget_object"></a>

### fget_object(bucket_name, object_name, file_path, request_headers=None, ssec=None, version_id=None, extra_query_params=None, tmp_file_path=None)
Downloads data of an object to file.

__Parameters__

| Param                | Type             | Description                                          |
|:---------------------|:-----------------|:-----------------------------------------------------|
| `bucket_name`        | _str_            | Name of the bucket.                                  |
| `object_name`        | _str_            | Object name in the bucket.                           |
| `file_path`          | _str_            | Name of file to download.                            |
| `request_headers`    | _dict_           | Any additional headers to be added with GET request. |
| `ssec`               | _SseCustomerKey_ | Server-side encryption customer key.                 |
| `version_id`         | _str_            | Version-ID of the object.                            |
| `extra_query_params` | _dict_           | Extra query parameters for advanced usage.           |
| `tmp_file_path`      | _str_            | Path to a temporary file.                            |

__Return Value__

| Return                         |
|:-------------------------------|
| Object information as _Object_ |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.sse import SseCustomerKey
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # Download data of an object.
    print("example one")
    await client.fget_object("my-bucket", "my-object", "my-filename")

    # Download data of an object of version-ID.
    print("example two")
    await client.fget_object(
        "my-bucket", "my-object", "my-filename",
        version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
    )

    # Download data of an SSE-C encrypted object.
    print("example three")
    await client.fget_object(
        "my-bucket", "my-object", "my-filename",
        ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
    )

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="copy_object"></a>

### copy_object(bucket_name, object_name, source, sse=None, metadata=None, tags=None, retention=None, legal_hold=False, metadata_directive=None, tagging_directive=None)

Create an object by server-side copying data from another object. In this API maximum supported source object size is 5GiB.

__Parameters__

| Param                | Type         | Description                                                           |
|:---------------------|:-------------|:----------------------------------------------------------------------|
| `bucket_name`        | _str_        | Name of the bucket.                                                   |
| `object_name`        | _str_        | Object name in the bucket.                                            |
| `source`             | _CopySource_ | Source object information.                                            |
| `sse`                | _Sse_        | Server-side encryption of destination object.                         |
| `metadata`           | _dict_       | Any user-defined metadata to be copied along with destination object. |
| `tags`               | _Tags_       | Tags for destination object.                                          |
| `retention`          | _Retention_  | Retention configuration.                                              |
| `legal_hold`         | _bool_       | Flag to set legal hold for destination object.                        |
| `metadata_directive` | _str_        | Directive used to handle user metadata for destination object.        |
| `tagging_directive`  | _str_        | Directive used to handle tags for destination object.                 |


__Return Value__

| Return                      |
|:----------------------------|
| _ObjectWriteResult_ object. |

__Example__

```py
from datetime import datetime, timezone
from miniopy_async import Minio
from miniopy_async.commonconfig import REPLACE, CopySource
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # copy an object from a bucket to another.
    print("example one")
    result = await client.copy_object(
        "my-job-bucket",
        "my-copied-object1",
        CopySource("my-bucket", "my-object"),
    )
    print(result.object_name, result.version_id)

    # copy an object with condition.
    print("example two")
    result = await client.copy_object(
        "my-job-bucket",
        "my-copied-object2",
        CopySource(
            "my-bucket",
            "my-object",
            modified_since=datetime(2014, 4, 1, tzinfo=timezone.utc),
        ),
    )
    print(result.object_name, result.version_id)

    # copy an object from a bucket with replacing metadata.
    print("example three")
    metadata = {"Content-Type": "application/octet-stream"}
    result = await client.copy_object(
        "my-job-bucket",
        "my-copied-object3",
        CopySource("my-bucket", "my-object"),
        metadata=metadata,
        metadata_directive=REPLACE,
    )
    print(result.object_name, result.version_id)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="compose_object"></a>

### compose_object(bucket_name, object_name, sources, sse=None, metadata=None, tags=None, retention=None, legal_hold=False)

Create an object by combining data from different source objects using server-side copy.

__Parameters__

| Param         | Type        | Description                                                           |
|:--------------|:------------|:----------------------------------------------------------------------|
| `bucket_name` | _str_       | Name of the bucket.                                                   |
| `object_name` | _str_       | Object name in the bucket.                                            |
| `sources`     | _list_      | List of _ComposeSource_ object.                                       |
| `sse`         | _Sse_       | Server-side encryption of destination object.                         |
| `metadata`    | _dict_      | Any user-defined metadata to be copied along with destination object. |
| `tags`        | _Tags_      | Tags for destination object.                                          |
| `retention`   | _Retention_ | Retention configuration.                                              |
| `legal_hold`  | _bool_      | Flag to set legal hold for destination object.                        |


__Return Value__

| Return                      |
|:----------------------------|
| _ObjectWriteResult_ object. |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.commonconfig import ComposeSource
from miniopy_async.sse import SseS3
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

# Each part must larger than 5MB
sources = [
    ComposeSource("my-job-bucket", "my-object-part-one"),
    ComposeSource("my-job-bucket", "my-object-part-two"),
    ComposeSource("my-job-bucket", "my-object-part-three"),
]

async def main():
    # Create my-bucket/my-object by combining source object
    # list.
    print('example one')
    result = await client.compose_object("my-bucket", "my-object", sources)
    print(result.object_name, result.version_id)

    # Create my-bucket/my-object with user metadata by combining
    # source object list.
    print('example two')
    result = await client.compose_object(
        "my-bucket",
        "my-object",
        sources,
        metadata={"Content-Type": "application/octet-stream"},
    )
    print(result.object_name, result.version_id)

    # Create my-bucket/my-object with user metadata and
    # server-side encryption by combining source object list.
    print('example three')
    result = await client.compose_object(
        "my-bucket",
        "my-object",
        sources,
        sse=SseS3()
    )
    print(result.object_name, result.version_id)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="put_object"></a>

### put_object(bucket_name, object_name, data, length, content_type="application/octet-stream", metadata=None, sse=None, progress=False, part_size=0, num_parallel_uploads=3, tags=None, retention=None, legal_hold=False)

Uploads data from a stream to an object in a bucket.

__Parameters__

| Param                  | Type        | Description                                                         |
|:-----------------------|:------------|:--------------------------------------------------------------------|
| `bucket_name`          | _str_       | Name of the bucket.                                                 |
| `object_name`          | _str_       | Object name in the bucket.                                          |
| `data`                 | _object_    | An object having callable read() returning bytes object.            |
| `length`               | _int_       | Data size; -1 for unknown size and set valid part_size.             |
| `content_type`         | _str_       | Content type of the object.                                         |
| `metadata`             | _dict_      | Any additional metadata to be uploaded along with your PUT request. |
| `sse`                  | _Sse_       | Server-side encryption.                                             |
| `progress`             | _bool_      | Flag to set whether to show progress.                               |
| `part_size`            | _int_       | Multipart part size.                                                |
| `num_parallel_uploads` | _int_       | Number of parallel uploads.                                         |
| `tags`                 | _Tags_      | Tags for the object.                                                |
| `retention`            | _Retention_ | Retention configuration.                                            |
| `legal_hold`           | _bool_      | Flag to set legal hold for the object.                              |

__Return Value__

| Return                      |
|:----------------------------|
| _ObjectWriteResult_ object. |

__Example__
```py
import io
from datetime import datetime, timedelta
from urllib.request import urlopen
from miniopy_async import Minio
from miniopy_async.commonconfig import GOVERNANCE, Tags
from miniopy_async.retention import Retention
from miniopy_async.sse import SseCustomerKey, SseKMS, SseS3
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # Upload data.
    print('example one')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload unknown sized data.
    print('example two')
    data = urlopen(
        "https://raw.githubusercontent.com/hlf20010508/miniopy-async/master/README.md",
    )
    result = await client.put_object(
        "my-bucket", "my-object", data, length=-1, part_size=10*1024*1024,
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with content-type.
    print('example three')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        content_type="application/csv",
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with metadata.
    print('example four')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        metadata={"Content-Type": "application/octet-stream"},
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with customer key type of server-side encryption.
    print('example five')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with KMS type of server-side encryption.
    print('example six')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        sse=SseKMS("KMS-KEY-ID", {"Key1": "Value1", "Key2": "Value2"}),
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with S3 type of server-side encryption.
    print('example seven')
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        sse=SseS3(),
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with tags, retention and legal-hold.
    print('example eight')
    date = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0,
    ) + timedelta(days=30)
    tags = Tags(for_object=True)
    tags["User"] = "jsmith"
    result = await client.put_object(
        "my-bucket", "my-object", io.BytesIO(b"hello"), 5,
        tags=tags,
        retention=Retention(GOVERNANCE, date),
        legal_hold=True,
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with showing progress status.
    print('example nine')
    result = await client.put_object(
        "transfer", "my-object", io.BytesIO(b"helloworld"*2000000), 20000000, progress=True
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="fput_object"></a>

### fput_object(bucket_name, object_name, file_path, content_type="application/octet-stream", metadata=None, sse=None, progress=False,  part_size=0, num_parallel_uploads=3,, tags=None, retention=None, legal_hold=False)

Uploads data from a file to an object in a bucket.

| Param                  | Type        | Description                                                         |
|:-----------------------|:------------|:--------------------------------------------------------------------|
| `bucket_name`          | _str_       | Name of the bucket.                                                 |
| `object_name`          | _str_       | Object name in the bucket.                                          |
| `file_path`            | _str_       | Name of file to upload.                                             |
| `content_type`         | _str_       | Content type of the object.                                         |
| `metadata`             | _dict_      | Any additional metadata to be uploaded along with your PUT request. |
| `sse`                  | _Sse_       | Server-side encryption.                                             |
| `progress`             | _bool_      | Flag to set whether to show progress.                               |
| `part_size`            | _int_       | Multipart part size.                                                |
| `num_parallel_uploads` | _int_       | Number of parallel uploads.                                         |
| `tags`                 | _Tags_      | Tags for the object.                                                |
| `retention`            | _Retention_ | Retention configuration.                                            |
| `legal_hold`           | _bool_      | Flag to set legal hold for the object.                              |

__Return Value__

| Return                      |
|:----------------------------|
| _ObjectWriteResult_ object. |

__Example__

```py
from datetime import datetime, timedelta
from miniopy_async import Minio
from miniopy_async.commonconfig import GOVERNANCE, Tags
from miniopy_async.retention import Retention
from miniopy_async.sse import SseCustomerKey, SseKMS, SseS3
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # Upload data.
    print("example one")
    result = await client.fput_object(
        "my-bucket", "my-object1", "my-filename",
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with content-type.
    print("example two")
    result = await client.fput_object(
        "my-bucket", "my-object2", "my-filename",
        content_type="application/octet-stream",
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with metadata.
    print("example three")
    result = await client.fput_object(
        "my-bucket", "my-object3", "my-filename",
        metadata={"Content-Type": "application/octet-stream"},
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with customer key type of server-side encryption.
    print("example four")
    result = await client.fput_object(
        "my-bucket", "my-object4", "my-filename",
        sse=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with KMS type of server-side encryption.
    print("example five")
    result = await client.fput_object(
        "my-bucket", "my-object5", "my-filename",
        sse=SseKMS("KMS-KEY-ID", {"Key1": "Value1", "Key2": "Value2"}),
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with S3 type of server-side encryption.
    print("example six")
    result = await client.fput_object(
        "my-bucket", "my-object6", "my-filename",
        sse=SseS3(),
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with tags, retention and legal-hold.
    print("example seven")
    date = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0,
    ) + timedelta(days=30)
    tags = Tags(for_object=True)
    tags["User"] = "jsmith"
    result = await client.fput_object(
        "my-bucket", "my-object7", "my-filename",
        tags=tags,
        retention=Retention(GOVERNANCE, date),
        legal_hold=True,
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

    # Upload data with showing progress status.
    print("example eight")
    result = await client.fput_object(
        "my-bucket", "my-object8", "my-filename", progress=True
    )
    print(
        "created {0} object; etag: {1}, version-id: {2}".format(
            result.object_name, result.etag, result.version_id,
        ),
    )

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="stat_object"></a>

### stat_object(bucket_name, object_name, ssec=None, version_id=None, extra_query_params=None)

Get object information and metadata of an object.

__Parameters__

| Param                | Type             | Description                                |
|:---------------------|:-----------------|:-------------------------------------------|
| `bucket_name`        | _str_            | Name of the bucket.                        |
| `object_name`        | _str_            | Object name in the bucket.                 |
| `ssec`               | _SseCustomerKey_ | Server-side encryption customer key.       |
| `version_id`         | _str_            | Version ID of the object.                  |
| `extra_query_params` | _dict_           | Extra query parameters for advanced usage. |

__Return Value__

| Return                         |
|:-------------------------------|
| Object information as _Object_ |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.sse import SseCustomerKey
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # Get object information.
    print('example one')
    result = await client.stat_object("my-bucket", "my-object")
    print(
        "status: last-modified: {0}, size: {1}".format(
            result.last_modified, result.size,
        ),
    )

    # Get object information of version-ID.
    print('example two')
    result = await client.stat_object(
        "my-bucket", "my-object",
        version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
    )
    print(
        "status: last-modified: {0}, size: {1}".format(
            result.last_modified, result.size,
        ),
    )

    # Get SSE-C encrypted object information.
    print('example three')
    result = await client.stat_object(
        "my-bucket", "my-object",
        ssec=SseCustomerKey(b"32byteslongsecretkeymustprovided"),
    )
    print(
        "status: last-modified: {0}, size: {1}".format(
            result.last_modified, result.size,
        ),
    )

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="remove_object"></a>

### remove_object(bucket_name, object_name, version_id=None)

Remove an object.

__Parameters__

| Param         | Type  | Description                |
|:--------------|:------|:---------------------------|
| `bucket_name` | _str_ | Name of the bucket.        |
| `object_name` | _str_ | Object name in the bucket. |
| `version_id`  | _str_ | Version ID of the object.  |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # Remove object.
    print('example one')
    await client.remove_object("my-bucket", "my-object")

    # Remove version of an object.
    print('example two')
    await client.remove_object(
        "my-bucket", "my-object",
        version_id="dfbd25b3-abec-4184-a4e8-5a35a5c1174d",
    )

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="remove_objects"></a>

### remove_objects(bucket_name, delete_object_list, bypass_governance_mode=False)

Remove multiple objects.

__Parameters__

| Param                    | Type       | Description                                                         |
|:-------------------------|:-----------|:--------------------------------------------------------------------|
| `bucket_name`            | _str_      | Name of the bucket.                                                 |
| `delete_object_list`     | _iterable_ | An iterable containing :class:`DeleteObject <DeleteObject>` object. |
| `bypass_governance_mode` | _bool_     | Bypass Governance retention mode.                                   |

__Return Value__

| Return                                                           |
|:-----------------------------------------------------------------|
| An iterator containing :class:`DeleteError <DeleteError>` object |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.deleteobjects import DeleteObject
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    # Remove list of objects.
    print('example one')
    errors = await client.remove_objects(
        "my-bucket",
        [
            DeleteObject("my-object1"),
            DeleteObject("my-object2"),
            DeleteObject("my-object3", "13f88b18-8dcd-4c83-88f2-8631fdb6250c"),
        ],
    )
    for error in errors:
        print("error occured when deleting object", error)

    # Remove a prefix recursively.
    print('example two')
    delete_object_list = [DeleteObject(obj.object_name)
        for obj in await client.list_objects(
            "my-bucket",
            "my/prefix/",
            recursive=True
        )
    ]
    errors = await client.remove_objects("my-bucket", delete_object_list)
    for error in errors:
        print("error occured when deleting object", error)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="delete_object_tags"></a>

### delete_object_tags(bucket_name, object_name, version_id=None)

Delete tags configuration of an object.

__Parameters__

| Param           | Type  | Description                |
|:----------------|:------|:---------------------------|
| ``bucket_name`` | _str_ | Name of the bucket.        |
| ``object_name`` | _str_ | Object name in the bucket. |
| ``version_id``  | _str_ | Version ID of the object.  |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.delete_object_tags("my-bucket")

loop=asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_object_tags"></a>

### get_object_tags(bucket_name, object_name, version_id=None)

Get tags configuration of an object.

__Parameters__

| Param           | Type  | Description                |
|:----------------|:------|:---------------------------|
| ``bucket_name`` | _str_ | Name of the bucket.        |
| ``object_name`` | _str_ | Object name in the bucket. |
| ``version_id``  | _str_ | Version ID of the object.  |

| Return         |
|:---------------|
| _Tags_ object. |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    tags = await client.get_object_tags("my-bucket", "my-object")
    print(tags)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_object_tags"></a>

### set_object_tags(bucket_name, object_name, tags, version_id=None)

Set tags configuration to an object.

__Parameters__

| Param           | Type   | Description                |
|:----------------|:-------|:---------------------------|
| ``bucket_name`` | _str_  | Name of the bucket.        |
| ``object_name`` | _str_  | Object name in the bucket. |
| ``tags``        | _Tags_ | Tags configuration.        |
| ``version_id``  | _str_  | Version ID of the object.  |

__Example__

```py
from miniopy_async import Minio
from miniopy_async.commonconfig import Tags
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

tags = Tags.new_object_tags()
tags["Project"] = "Project One"
tags["User"] = "jsmith"

async def main():
    await client.set_object_tags("my-bucket", "my-object", tags)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="enable_object_legal_hold"></a>

### enable_object_legal_hold(bucket_name, object_name, version_id=None)

Enable legal hold on an object.

__Parameters__

| Param         | Type  | Description                |
|:--------------|:------|:---------------------------|
| `bucket_name` | _str_ | Name of the bucket.        |
| `object_name` | _str_ | Object name in the bucket. |
| `version_id`  | _str_ | Version ID of the object.  |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.enable_object_legal_hold("my-bucket", "my-object")

loop=asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="disable_object_legal_hold"></a>

### disable_object_legal_hold(bucket_name, object_name, version_id=None)

Disable legal hold on an object.

__Parameters__

| Param         | Type  | Description                |
|:--------------|:------|:---------------------------|
| `bucket_name` | _str_ | Name of the bucket.        |
| `object_name` | _str_ | Object name in the bucket. |
| `version_id`  | _str_ | Version ID of the object.  |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    await client.disable_object_legal_hold("my-bucket", "my-object")

loop=asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="is_object_legal_hold_enabled"></a>

### is_object_legal_hold_enabled(bucket_name, object_name, version_id=None)

Returns true if legal hold is enabled on an object.

__Parameters__

| Param         | Type  | Description                |
|:--------------|:------|:---------------------------|
| `bucket_name` | _str_ | Name of the bucket.        |
| `object_name` | _str_ | Object name in the bucket. |
| `version_id`  | _str_ | Version ID of the object.  |

__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    if await client.is_object_legal_hold_enabled("my-bucket", "my-object"):
        print("legal hold is enabled on my-object")
    else:
        print("legal hold is not enabled on my-object")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_object_retention"></a>

### get_object_retention(bucket_name, object_name, version_id=None)

Get retention information of an object.

__Parameters__

| Param                | Type             | Description                                |
|:---------------------|:-----------------|:-------------------------------------------|
| `bucket_name`        | _str_            | Name of the bucket.                        |
| `object_name`        | _str_            | Object name in the bucket.                 |
| `version_id`         | _str_            | Version ID of the object.                  |

__Return Value__

| Return             |
|:-------------------|
| _Retention_ object |


__Example__

```py
from miniopy_async import Minio
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

async def main():
    config = await client.get_object_retention("my-bucket", "my-object")
    print(config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="set_object_retention"></a>

### set_object_retention(bucket_name, object_name, config, version_id=None)

Set retention information to an object.

__Parameters__

| Param         | Type        | Description                |
|:--------------|:------------|:---------------------------|
| `bucket_name` | _str_       | Name of the bucket.        |
| `object_name` | _str_       | Object name in the bucket. |
| `config`      | _Retention_ | Retention configuration.   |
| `version_id`  | _str_       | Version ID of the object.  |

__Example__

```py
from datetime import datetime, timedelta
from miniopy_async import Minio
from miniopy_async.commonconfig import GOVERNANCE
from miniopy_async.retention import Retention
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

config = Retention(GOVERNANCE, datetime.utcnow() + timedelta(days=10))

async def main():
    await client.set_object_retention("my-bucket", "my-object", config)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="presigned_get_object"></a>

### presigned_get_object(bucket_name, object_name, expires=timedelta(days=7), response_headers=None, request_date=None, version_id=None, extra_query_params=None, change_host=None)

Get presigned URL of an object to download its data with expiry time and custom request parameters.

__Parameters__

| Param                | Type                 | Description                                                                                                          |
|:---------------------|:---------------------|:---------------------------------------------------------------------------------------------------------------------|
| `bucket_name`        | _str_                | Name of the bucket.                                                                                                  |
| `object_name`        | _str_                | Object name in the bucket.                                                                                           |
| `expires`            | _datetime.timedelta_ | Expiry in seconds; defaults to 7 days.                                                                               |
| `response_headers`   | _dict_               | Optional response_headers argument to specify response fields like date, size, type of file, data about server, etc. |
| `request_date`       | _datetime.datetime_  | Optional request_date argument to specify a different request date. Default is current date.                         |
| `version_id`         | _str_                | Version ID of the object.                                                                                            |
| `extra_query_params` | _dict_               | Extra query parameters for advanced usage.                                                                           |
| `change_host`        | _str_                | Change the host for this presign temporaryly. This parameter is for the circumstance in which your base url is set with private IP address such as 127.0.0.1 or 0.0.0.0 and you want to create a url with public IP address. |

__Return Value__

| Return     |
|:-----------|
| URL string |

__Example__

```py
from datetime import timedelta
from miniopy_async import Minio
import asyncio

async def main():
    client = Minio(
        "play.min.io",
        access_key="Q3AM3UQ867SPQQA43P2F",
        secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
        secure=True  # http for False, https for True
    )

    # Get presigned URL string to download 'my-object' in
    # 'my-bucket' with default expiry (i.e. 7 days).
    print('example one')
    url = await client.presigned_get_object("my-bucket", "my-object")
    print('url:', url)

    # Get presigned URL string to download 'my-object' in
    # 'my-bucket' with two hours expiry.
    print('example two')
    url = await client.presigned_get_object(
        "my-bucket", "my-object", expires=timedelta(hours=2),
    )
    print('url:', url)

    # Get presigned URL string to download 'my-object' in
    # 'my-bucket' with public IP address when using private IP address.
    client = Minio(
        "127.0.0.1:9000",
        access_key="your access key",
        secret_key="you secret key",
        secure=False  # http for False, https for True
    )

    print('example three')
    url = await client.presigned_get_object(
        "my-bucket",
        "my-object",
        change_host='https://YOURHOST:YOURPORT',
    )
    print('url:', url)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="presigned_put_object"></a>

### presigned_put_object(bucket_name, object_name, expires=timedelta(days=7), change_host=None)

Get presigned URL of an object to upload data with expiry time and custom request parameters.

__Parameters__

| Param         | Type                 | Description                            |
|:--------------|:---------------------|:---------------------------------------|
| `bucket_name` | _str_                | Name of the bucket.                    |
| `object_name` | _str_                | Object name in the bucket.             |
| `expires`     | _datetime.timedelta_ | Expiry in seconds; defaults to 7 days. |
| `change_host` | _str_                | Change the host for this presign temporaryly. This parameter is for the circumstance in which your base url is set with private IP address such as 127.0.0.1 or 0.0.0.0 and you want to create a url with public IP address. |

__Return Value__

| Return     |
|:-----------|
| URL string |

__Example__

```py
from datetime import timedelta
from miniopy_async import Minio
import asyncio

async def main():
    client = Minio(
        "play.min.io",
        access_key="Q3AM3UQ867SPQQA43P2F",
        secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
        secure=True  # http for False, https for True
    )

    # Get presigned URL string to upload data to 'my-object' in
    # 'my-bucket' with default expiry (i.e. 7 days).
    url = await client.presigned_put_object("my-bucket", "my-object")
    print('url:', url)

    # Get presigned URL string to upload data to 'my-object' in
    # 'my-bucket' with two hours expiry.
    url = await client.presigned_put_object(
        "my-bucket", "my-object", expires=timedelta(hours=2),
    )
    print('url:', url)

    # Get presigned URL string to upload data to 'my-object' in
    # 'my-bucket' with public IP address when using private IP address.
    client = Minio(
        "127.0.0.1:9000",
        access_key="your access key",
        secret_key="you secret key",
        secure=False  # http for False, https for True
    )

    print('example three')
    url = await client.presigned_put_object(
        "my-bucket",
        "my-object",
        change_host='https://YOURHOST:YOURPORT',
    )
    print('url:', url)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="presigned_post_policy"></a>

### presigned_post_policy(policy)

Get form-data of PostPolicy of an object to upload its data using POST method.

__Parameters__

| Param    | Type         | Description  |
|:---------|:-------------|:-------------|
| `policy` | _PostPolicy_ | Post policy. |

__Return Value__

| Return                      |
|:----------------------------|
| Form-data containing _dict_ |

__Example__

```py
from datetime import datetime, timedelta
from miniopy_async import Minio
from miniopy_async.datatypes import PostPolicy
import asyncio

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

policy = PostPolicy(
    "my-bucket", datetime.utcnow() + timedelta(days=10),
)
policy.add_starts_with_condition("key", "my/object/prefix/")
policy.add_content_length_range_condition(1*1024*1024, 10*1024*1024)

async def main():
    form_data = await client.presigned_post_policy(policy)
    curl_cmd = (
        "curl -X POST "
        "https://play.min.io/my-bucket "
        "{0} -F file=@<FILE>"
    ).format(
        " ".join(["-F {0}={1}".format(k, v) for k, v in form_data.items()]),
    )
    print('curl_cmd:',curl_cmd)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

<a id="get_presigned_url"></a>

### get_presigned_url(method, bucket_name, object_name, expires=timedelta(days=7), response_headers=None, request_date=None, version_id=None, extra_query_params=None, change_host=None)

Get presigned URL of an object for HTTP method, expiry time and custom request parameters.

__Parameters__
| Param                | Type                 | Description                                                                                                          |
|:---------------------|:---------------------|:---------------------------------------------------------------------------------------------------------------------|
| `method`             | _str_                | HTTP method.                                                                                                         |
| `bucket_name`        | _str_                | Name of the bucket.                                                                                                  |
| `object_name`        | _str_                | Object name in the bucket.                                                                                           |
| `expires`            | _datetime.timedelta_ | Expiry in seconds; defaults to 7 days.                                                                               |
| `response_headers`   | _dict_               | Optional response_headers argument to specify response fields like date, size, type of file, data about server, etc. |
| `request_date`       | _datetime.datetime_  | Optional request_date argument to specify a different request date. Default is current date.                         |
| `version_id`         | _str_                | Version ID of the object.                                                                                            |
| `extra_query_params` | _dict_               | Extra query parameters for advanced usage.                                                                           |
| `change_host`        | _str_                | Change the host for this presign temporaryly. This parameter is for the circumstance in which your base url is set with private IP address such as 127.0.0.1 or 0.0.0.0 and you want to create a url with public IP address. |

__Return Value__

| Return     |
|:-----------|
| URL string |

__Example__

```py
from datetime import timedelta
from miniopy_async import Minio
import asyncio

async def main():
    client = Minio(
        "play.min.io",
        access_key="Q3AM3UQ867SPQQA43P2F",
        secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
        secure=True  # http for False, https for True
    )
    # Get presigned URL string to delete 'my-object' in
    # 'my-bucket' with one day expiry.
    print('example one')
    url = await client.get_presigned_url(
        "DELETE",
        "my-bucket",
        "my-object",
        expires=timedelta(days=1),
    )
    print('url:', url)

    # Get presigned URL string to upload 'my-object' in
    # 'my-bucket' with response-content-type as application/json
    # and one day expiry.
    print('example two')
    url = await client.get_presigned_url(
        "PUT",
        "my-bucket",
        "my-object",
        expires=timedelta(days=1),
        response_headers={"response-content-type": "application/json"},
    )
    print('url:', url)

    # Get presigned URL string to download 'my-object' in
    # 'my-bucket' with two hours expiry.
    print('example three')
    url = await client.get_presigned_url(
        "GET",
        "my-bucket",
        "my-object",
        expires=timedelta(hours=2),
    )
    print('url:', url)

    # Get presigned URL string to download 'my-object' in
    # 'my-bucket' with public IP address when using private IP address.
    client = Minio(
        "127.0.0.1:9000",
        access_key="your access key",
        secret_key="you secret key",
        secure=False  # http for False, https for True
    )

    print('example four')
    url = await client.get_presigned_url(
        "GET",
        "my-bucket",
        "my-object",
        change_host='https://YOURHOST:YOURPORT',
    )
    print('url:', url)
    

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```
