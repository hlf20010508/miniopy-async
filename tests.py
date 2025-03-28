import unittest
from miniopy_async import Minio
from miniopy_async.commonconfig import (
    ComposeSource,
    CopySource,
    ENABLED,
    Filter,
    Tags,
    SnowballObject,
)
from miniopy_async.lifecycleconfig import Expiration, LifecycleConfig, Rule as lcRule
from miniopy_async.time import utcnow
from miniopy_async.versioningconfig import VersioningConfig
from miniopy_async.sseconfig import Rule as sseRule, SSEConfig
from miniopy_async.datatypes import PostPolicy
from miniopy_async.deleteobjects import DeleteObject
from miniopy_async.select import (
    CSVInputSerialization,
    CSVOutputSerialization,
    SelectRequest,
)
import asyncio
import os
import json
from datetime import datetime, timedelta
import aiohttp
from io import BytesIO
import warnings


class Test(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter("ignore", ResourceWarning)
        cls.client = Minio(
            "play.min.io",
            access_key="Q3AM3UQ867SPQQA43P2F",
            secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
            secure=True,  # http for False, https for True
        )
        cls.bucket_name = "miniopy-async"
        cls.test_file_name = "testfile"
        asyncio.run(cls.create_bucket())

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.remove_bucket())

    @classmethod
    async def create_bucket(cls):
        if not await cls.client.bucket_exists(cls.bucket_name):
            await cls.client.make_bucket(cls.bucket_name)

    @classmethod
    async def remove_bucket(cls):
        if await cls.client.bucket_exists(cls.bucket_name):
            objects = await cls.client.list_objects(
                cls.bucket_name, include_version=True
            )
            await cls.client.remove_objects(
                cls.bucket_name,
                [DeleteObject(obj.object_name, obj.version_id) for obj in objects],
            )
            await cls.client.remove_bucket(cls.bucket_name)

    async def asyncTearDown(self):
        await asyncio.sleep(5)

    async def recreate_bucket(self):
        await self.remove_bucket()
        await self.create_bucket()

    async def put_test_file(
        self,
        filename: str | None = None,
        content: bytes = b"hello" * 1024 * 1024,
    ):
        test_content = BytesIO(content)
        await self.client.put_object(
            self.bucket_name,
            filename if filename else self.test_file_name,
            test_content,
            length=test_content.getbuffer().nbytes,
        )

    async def test_put_object(self):
        test_content = BytesIO(b"hello" * 1024 * 1024)
        await self.client.put_object(
            self.bucket_name,
            self.test_file_name,
            test_content,
            length=test_content.getbuffer().nbytes,
        )

    async def test_fput_object(self):
        with open(self.test_file_name, "wb") as file:
            file.write(b"hello" * 1024 * 1024)
        self.addCleanup(os.remove, self.test_file_name)

        await self.client.fput_object(
            self.bucket_name,
            self.test_file_name,
            self.test_file_name,
        )

    async def test_upload_snowball_objects(self):
        test_content1 = BytesIO(b"hello" * 1024 * 1024)
        test_content2 = BytesIO(b"world" * 1024 * 1024)

        await self.client.upload_snowball_objects(
            self.bucket_name,
            [
                SnowballObject(
                    "testfile-1",
                    data=test_content1,
                    length=test_content1.getbuffer().nbytes,
                ),
                SnowballObject(
                    "testfile-2",
                    data=test_content2,
                    length=test_content2.getbuffer().nbytes,
                    mod_time=datetime.now(),
                ),
            ],
            staging_filename="testfiles.tar",
        )
        self.addCleanup(os.remove, "testfiles.tar")

    async def test_compose_object(self):
        test_file_names = ["testfile-1", "testfile-2"]
        for test_file_name in test_file_names:
            await self.put_test_file(test_file_name)

        sources = [
            ComposeSource(self.bucket_name, test_file_name)
            for test_file_name in test_file_names
        ]
        await self.client.compose_object(self.bucket_name, "composed-object", sources)

    async def test_copy_object(self):
        await self.put_test_file()

        await self.client.copy_object(
            self.bucket_name,
            "copied-object",
            CopySource(self.bucket_name, self.test_file_name),
        )

    async def test_set_bucket_versioning(self):
        await self.client.set_bucket_versioning(
            self.bucket_name, VersioningConfig(ENABLED)
        )
        await self.recreate_bucket()

    async def test_set_bucket_encryption(self):
        await self.client.set_bucket_encryption(
            self.bucket_name,
            SSEConfig(sseRule.new_sse_s3_rule()),
        )
        await self.recreate_bucket()

    async def test_set_bucket_lifecycle(self):
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
        await self.client.set_bucket_lifecycle(self.bucket_name, lifecycle_config)
        await self.recreate_bucket()

    async def test_set_bucket_policy(self):
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                    "Resource": "arn:aws:s3:::%s" % self.bucket_name,
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::%s/*" % self.bucket_name,
                },
            ],
        }
        await self.client.set_bucket_policy(self.bucket_name, json.dumps(bucket_policy))
        await self.recreate_bucket()

    async def test_set_bucket_tags(self):
        bucket_tags = Tags.new_bucket_tags()
        bucket_tags["Project"] = "Project One"
        bucket_tags["User"] = "jsmith"
        await self.client.set_bucket_tags(self.bucket_name, bucket_tags)
        await self.recreate_bucket()

    async def test_set_object_tags(self):
        await self.put_test_file()

        object_tags = Tags.new_object_tags()
        object_tags["Project"] = "Project One"
        object_tags["User"] = "jsmith"
        await self.client.set_object_tags(
            self.bucket_name, self.test_file_name, object_tags
        )

    async def test_stat_object(self):
        await self.put_test_file()

        await self.client.stat_object(self.bucket_name, self.test_file_name)

    async def test_presigned_get_object(self):
        await self.put_test_file()

        await self.client.presigned_get_object(self.bucket_name, self.test_file_name)

    async def test_presigned_put_object(self):
        await self.client.presigned_put_object(self.bucket_name, self.test_file_name)

    async def test_presigned_post_policy(self):
        bucket_post_policy = PostPolicy(
            self.bucket_name,
            utcnow() + timedelta(days=10),
        )
        bucket_post_policy.add_starts_with_condition("key", "my/object/prefix/")
        bucket_post_policy.add_content_length_range_condition(
            1 * 1024 * 1024, 10 * 1024 * 1024
        )
        await self.client.presigned_post_policy(bucket_post_policy)

    async def test_list_buckets(self):
        await self.client.list_buckets()

    async def test_list_objects(self):
        await self.client.list_objects(self.bucket_name)

    async def test_get_object(self):
        await self.put_test_file()

        async with aiohttp.ClientSession() as session:
            response = await self.client.get_object(
                self.bucket_name, self.test_file_name, session
            )
            await response.content.read()

    async def test_fget_object(self):
        await self.client.fget_object(
            self.bucket_name, self.test_file_name, self.test_file_name
        )
        self.addCleanup(os.remove, self.test_file_name)

    async def test_select_object_content(self):
        await self.put_test_file(content=b"hello")

        result = await self.client.select_object_content(
            self.bucket_name,
            self.test_file_name,
            SelectRequest(
                "select * from s3object",
                CSVInputSerialization(),
                CSVOutputSerialization(),
                request_progress=True,
            ),
        )
        async for data in result.stream():
            data.decode()

    async def test_remove_object(self):
        await self.put_test_file()

        await self.client.remove_object(self.bucket_name, self.test_file_name)

    async def test_list_object_versions(self):
        await self.client.list_object_versions(self.bucket_name)


if __name__ == "__main__":
    unittest.main()
