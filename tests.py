from miniopy_async import Minio
from miniopy_async.commonconfig import (
    ComposeSource,
    CopySource,
    ENABLED,
    Filter,
    Tags,
)
from miniopy_async.lifecycleconfig import Expiration, LifecycleConfig, Rule as lcRule
from miniopy_async.versioningconfig import VersioningConfig
from miniopy_async.sseconfig import Rule as sseRule, SSEConfig
from miniopy_async.datatypes import PostPolicy
from miniopy_async.deleteobjects import DeleteObject
from miniopy_async.select import (
    CSVInputSerialization,
    CSVOutputSerialization,
    SelectRequest,
)
from aiostream.stream import list as alist
import asyncio
import os
import json
from datetime import datetime, timedelta
import traceback

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,  # http for False, https for True
)

bucket_name = "my-bucket"
test_file_name = ["testfile-1", "testfile-2"]

error_func_list = []


async def create_bucket():
    try:
        if not await client.bucket_exists(bucket_name):
            await client.make_bucket(bucket_name)
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("create_bucket")


async def put_object():
    try:
        test_content = b"1" * 1024 * 1024 * 5  # 5MB
        for file_name in test_file_name:
            with open(file_name, "wb") as file:
                file.write(test_content)
            await client.fput_object(bucket_name, file_name, file_name)
            os.remove(file_name)
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("put_object")


async def compose_object():
    try:
        sources = [
            ComposeSource(bucket_name, file_name) for file_name in test_file_name
        ]
        await client.compose_object(bucket_name, "composed-object", sources)
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("compose_object")


async def copy_object():
    try:
        await client.copy_object(
            bucket_name,
            "copied-object",
            CopySource(bucket_name, test_file_name[0]),
        )
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("copy_object")


async def set_bucket_versioning():
    try:
        await client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("set_bucket_versioning")


async def set_bucket_encryption():
    try:
        await client.set_bucket_encryption(
            bucket_name,
            SSEConfig(sseRule.new_sse_s3_rule()),
        )
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("set_bucket_encryption")


async def set_bucket_lifecycle():
    try:
        lifecycle_config = LifecycleConfig(
            [
                lcRule(
                    ENABLED,
                    rule_filter=Filter(prefix="logs/"),
                    rule_id="rule2",
                    expiration=Expiration(days=365),
                ),
            ],
        )
        await client.set_bucket_lifecycle(bucket_name, lifecycle_config)
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("set_bucket_lifecycle")


async def set_bucket_policy():
    try:
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                    "Resource": "arn:aws:s3:::%s" % bucket_name,
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::%s/*" % bucket_name,
                },
            ],
        }
        await client.set_bucket_policy(bucket_name, json.dumps(bucket_policy))
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("set_bucket_policy")


async def set_bucket_tags():
    try:
        bucket_tags = Tags.new_bucket_tags()
        bucket_tags["Project"] = "Project One"
        bucket_tags["User"] = "jsmith"
        await client.set_bucket_tags(bucket_name, bucket_tags)
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("set_bucket_tags")


async def set_object_tags():
    try:
        object_tags = Tags.new_object_tags()
        object_tags["Project"] = "Project One"
        object_tags["User"] = "jsmith"
        await client.set_object_tags(bucket_name, test_file_name[0], object_tags)
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("set_object_tags")


async def stat_object():
    try:
        await client.stat_object(bucket_name, test_file_name[0])
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("stat_object")


async def presigned_get_object():
    try:
        await client.presigned_get_object(bucket_name, test_file_name[0])
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("presigned_get_object")


async def presigned_put_object():
    try:
        await client.presigned_put_object(bucket_name, test_file_name[0])
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("presigned_put_object")


async def presigned_post_policy():
    try:
        bucket_post_policy = PostPolicy(
            "my-bucket",
            datetime.utcnow() + timedelta(days=10),
        )
        bucket_post_policy.add_starts_with_condition("key", "my/object/prefix/")
        bucket_post_policy.add_content_length_range_condition(
            1 * 1024 * 1024, 10 * 1024 * 1024
        )
        await client.presigned_post_policy(bucket_post_policy)
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("presigned_post_policy")


async def list_buckets():
    try:
        await client.list_buckets()
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("list_buckets")


async def list_objects():
    try:
        await client.list_objects(bucket_name)
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("list_objects")


async def get_object():
    try:
        await client.fget_object(bucket_name, test_file_name[0], "testfile")
        os.remove("testfile")
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("get_object")


async def select_object_content():
    try:
        test_content = b"1" * 1024 * 512
        file_name = 'testfile-3'
        with open(file_name, "wb") as file:
            file.write(test_content)
        await client.fput_object(bucket_name, file_name, file_name)
        os.remove(file_name)
        result = await client.select_object_content(
            bucket_name,
            file_name,
            SelectRequest(
                "select * from s3object",
                CSVInputSerialization(),
                CSVOutputSerialization(),
                request_progress=True,
            ),
        )
        for data in await alist(result.stream()):
            data.decode()
    except:
        traceback.print_exc()
        error_func_list.append("select_object_content")


async def remove_object():
    try:
        await client.remove_object(bucket_name, test_file_name[0])
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("remove_object")


async def remove_objects():
    try:
        objs = await client.list_objects(bucket_name, include_version=True)
        await client.remove_objects(
            bucket_name,
            [DeleteObject(obj.object_name, obj.version_id) for obj in objs],
        )
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("remove_objects")


async def remove_bucket():
    try:
        await client.remove_bucket(bucket_name)
        print("Pass")
    except:
        traceback.print_exc()
        error_func_list.append("remove_bucket")


async def main():
    print("Testing create bucket...")
    await create_bucket()
    print("Testing put object...")
    await put_object()
    print("Testing compose object..")
    await compose_object()
    print("Testing copy object...")
    await copy_object()
    print("Testing set bucket versioning...")
    await set_bucket_versioning()
    print("Testing set bucket encryption...")
    await set_bucket_encryption()
    print("Testing set bucket lifecycle...")
    await set_bucket_lifecycle()
    print("Testing set bucket policy...")
    await set_bucket_policy()
    print("Testing set bucket tags...")
    await set_bucket_tags()
    print("Testing set object tags...")
    await set_object_tags()
    print("Testing stat object...")
    await stat_object()
    print("Testing presigned get object...")
    await presigned_get_object()
    print("Testing presigned put object...")
    await presigned_put_object()
    print("Testing presigned post policy...")
    await presigned_post_policy()
    print("Testing list bucket...")
    await list_buckets()
    print("Testing list objects...")
    await list_objects()
    print("Testing get object...")
    await get_object()
    print("Testing select object content...")
    await select_object_content()
    print("Testing remove object...")
    await remove_object()
    print("Testing remove objects...")
    await remove_objects()
    print("Testing remove bucket...")
    await remove_bucket()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()

if len(error_func_list) == 0:
    print("\nAll Pass")
else:
    print("\nError Functions:")
    for error_func in error_func_list:
        print(error_func)
