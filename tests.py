import asyncio
import json
import os
import unittest
import warnings
from datetime import datetime, timedelta
from io import BytesIO
from typing import cast

from faker import Faker

from miniopy_async import Minio, S3Error
from miniopy_async.commonconfig import (
    ENABLED,
    ComposeSource,
    CopySource,
    Filter,
    SnowballObject,
    Tags,
)
from miniopy_async.datatypes import PostPolicy
from miniopy_async.deleteobjects import DeleteObject
from miniopy_async.lifecycleconfig import Expiration, LifecycleConfig
from miniopy_async.lifecycleconfig import Rule as lcRule
from miniopy_async.select import (
    CSVInputSerialization,
    CSVOutputSerialization,
    SelectRequest,
)
from miniopy_async.sseconfig import Rule as sseRule
from miniopy_async.sseconfig import SSEConfig
from miniopy_async.time import utcnow
from miniopy_async.versioningconfig import VersioningConfig

fake = Faker()


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

        async def create_bucket():
            await cls.create_bucket()
            await cls.client.close_session()

        asyncio.run(create_bucket())

    async def asyncSetUp(self):
        self.client._ensure_session()

    async def asyncTearDown(self):
        await self.client.close_session()
        await asyncio.sleep(5)

    @classmethod
    def tearDownClass(cls):
        async def remove_bucket():
            cls.client._ensure_session()
            await cls.remove_bucket()
            await cls.client.close_session()

        asyncio.run(remove_bucket())

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
                [
                    DeleteObject(cast(str, obj.object_name), obj.version_id)
                    for obj in objects
                ],
            )
            await cls.client.remove_bucket(cls.bucket_name)

    async def recreate_bucket(self):
        await self.remove_bucket()
        await self.create_bucket()

    async def put_test_file(
        self,
        filename: str | None = None,
        content: bytes = fake.binary(5 * 1024 * 1024),
    ):
        test_content = BytesIO(content)
        await self.client.put_object(
            self.bucket_name,
            filename if filename else self.test_file_name,
            test_content,
            length=test_content.getbuffer().nbytes,
        )

    async def test_put_object(self):
        raw_content = fake.binary(5 * 1024 * 1024)
        test_content = BytesIO(raw_content)
        result = await self.client.put_object(
            self.bucket_name,
            self.test_file_name,
            test_content,
            length=test_content.getbuffer().nbytes,
        )

        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, self.test_file_name)
        self.assertEqual(
            await (
                await self.client.get_object(self.bucket_name, self.test_file_name)
            ).read(),
            raw_content,
        )

        raw_content = fake.binary(2 * 5 * 1024 * 1024)
        test_content = BytesIO(raw_content)
        result = await self.client.put_object(
            self.bucket_name,
            self.test_file_name,
            test_content,
            length=test_content.getbuffer().nbytes,
        )

        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, self.test_file_name)
        self.assertEqual(
            await (
                await self.client.get_object(self.bucket_name, self.test_file_name)
            ).read(),
            raw_content,
        )

    # unsupported on play.min.io yet
    # async def test_append_object(self):
    #     raw_content = fake.binary(1024 * 1024)
    #     test_content = BytesIO(raw_content)
    #     await self.client.put_object(
    #         self.bucket_name,
    #         self.test_file_name,
    #         test_content,
    #         length=test_content.getbuffer().nbytes,
    #     )

    #     raw_append_content = fake.binary(1024 * 1024)
    #     test_content = BytesIO(raw_append_content)
    #     result = await self.client.append_object(
    #         self.bucket_name,
    #         self.test_file_name,
    #         test_content,
    #         length=test_content.getbuffer().nbytes,
    #     )

    #     self.assertEqual(result.bucket_name, self.bucket_name)
    #     self.assertEqual(result.object_name, self.test_file_name)
    #     self.assertEqual(
    #         await (
    #             await self.client.get_object(self.bucket_name, self.test_file_name)
    #         ).read(),
    #         raw_content + raw_append_content,
    #     )

    async def test_fput_object(self):
        raw_content = fake.binary(5 * 1024 * 1024)
        file_name = f"{self.test_file_name}-1"
        with open(file_name, "wb") as file:
            file.write(raw_content)
        self.addCleanup(os.remove, file_name)

        result = await self.client.fput_object(
            self.bucket_name,
            file_name,
            file_name,
        )

        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, file_name)
        self.assertEqual(
            await (await self.client.get_object(self.bucket_name, file_name)).read(),
            raw_content,
        )

        raw_content = fake.binary(2 * 5 * 1024 * 1024)
        file_name = f"{self.test_file_name}-2"
        with open(file_name, "wb") as file:
            file.write(raw_content)
        self.addCleanup(os.remove, file_name)

        result = await self.client.fput_object(
            self.bucket_name,
            file_name,
            file_name,
        )

        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, file_name)
        self.assertEqual(
            await (await self.client.get_object(self.bucket_name, file_name)).read(),
            raw_content,
        )

    async def test_upload_snowball_objects(self):
        test_content1 = BytesIO(fake.binary(5 * 1024 * 1024))
        test_content2 = BytesIO(fake.binary(2 * 5 * 1024 * 1024))

        result = await self.client.upload_snowball_objects(
            self.bucket_name,
            [
                SnowballObject(
                    "test_snowball_file-1",
                    data=test_content1,
                    length=test_content1.getbuffer().nbytes,
                ),
                SnowballObject(
                    "test_snowball_file-2",
                    data=test_content2,
                    length=test_content2.getbuffer().nbytes,
                    mod_time=datetime.now(),
                ),
            ],
            staging_filename="testfiles.tar",
        )
        self.addCleanup(os.remove, "testfiles.tar")

        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertTrue(result.object_name.startswith("snowball."))
        self.assertTrue(result.object_name.endswith(".tar"))
        self.assertEqual(
            len(await self.client.list_objects(self.bucket_name, "test_snowball_file")),
            2,
        )
        self.assertEqual(
            len(await self.client.list_objects(self.bucket_name, "snowball")), 0
        )

    async def test_compose_object(self):
        test_file_names = ["testfile-1", "testfile-2"]
        for test_file_name in test_file_names:
            await self.put_test_file(test_file_name)

        sources = [
            ComposeSource(self.bucket_name, test_file_name)
            for test_file_name in test_file_names
        ]
        compose_name = "composed-object"
        result = await self.client.compose_object(
            self.bucket_name, compose_name, sources
        )

        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, compose_name)

    async def test_multipart_uploader(self):
        test_part1 = fake.binary(5 * 1024 * 1024)
        test_part2 = fake.binary(1 * 1024 * 1024)

        async with self.client.multipart_uploader(
            self.bucket_name, self.test_file_name
        ) as uploader:
            await uploader.upload_part(test_part1, part_number=1)
            await uploader.upload_part(test_part2, part_number=2)
        result = uploader.result
        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, self.test_file_name)
        self.assertEqual(
            await (
                await self.client.get_object(self.bucket_name, self.test_file_name)
            ).read(),
            test_part1 + test_part2,
        )

        test_part1 = fake.binary(5 * 1024 * 1024)
        test_part2 = fake.binary(1 * 1024 * 1024)

        uploader = self.client.multipart_uploader(self.bucket_name, self.test_file_name)
        await uploader.upload_part(test_part1, part_number=1)
        await uploader.upload_part(test_part2, part_number=2)
        result = await uploader.complete()
        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, self.test_file_name)
        self.assertEqual(
            await (
                await self.client.get_object(self.bucket_name, self.test_file_name)
            ).read(),
            test_part1 + test_part2,
        )

        await self.client.remove_object(self.bucket_name, self.test_file_name)
        uploader = self.client.multipart_uploader(self.bucket_name, self.test_file_name)
        await uploader.upload_part(test_part1, part_number=1)
        await uploader.abort()
        with self.assertRaises(ValueError):
            uploader.result
        with self.assertRaises(S3Error):
            await self.client.stat_object(self.bucket_name, self.test_file_name)

        test_part1 = fake.binary(1 * 1024 * 1024)
        test_part2 = fake.binary(5 * 1024 * 1024)

        uploader = self.client.multipart_uploader(self.bucket_name, self.test_file_name)
        await uploader.upload_part(test_part1, part_number=1)
        await uploader.upload_part(test_part2, part_number=2)
        with self.assertRaises(S3Error):
            await uploader.complete()
        with self.assertRaises(S3Error):
            await self.client.stat_object(self.bucket_name, self.test_file_name)

    async def test_copy_object(self):
        await self.put_test_file()

        copy_name = "copied-object"
        result = await self.client.copy_object(
            self.bucket_name,
            copy_name,
            CopySource(self.bucket_name, self.test_file_name),
        )

        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, copy_name)

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

        result = await self.client.stat_object(self.bucket_name, self.test_file_name)

        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, self.test_file_name)
        self.assertEqual(result.size, 5 * 1024 * 1024)

    async def test_get_presigned_url(self):
        await self.put_test_file()

        result = await self.client.get_presigned_url(
            "GET", self.bucket_name, self.test_file_name
        )

        self.assertTrue(result.startswith("https://play.min.io/"))

        client = Minio(
            "play.min.io",
            access_key="Q3AM3UQ867SPQQA43P2F",
            secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
            secure=True,  # http for False, https for True
            server_url="https://example.com",
        )

        async with client:
            result = await client.get_presigned_url(
                "GET", self.bucket_name, self.test_file_name
            )

        self.assertTrue(result.startswith("https://example.com/"))

    async def test_presigned_get_object(self):
        await self.put_test_file()

        result = await self.client.presigned_get_object(
            self.bucket_name, self.test_file_name
        )

        self.assertTrue(result.startswith("https://play.min.io/"))

    async def test_presigned_put_object(self):
        result = await self.client.presigned_put_object(
            self.bucket_name, self.test_file_name
        )

        self.assertTrue(result.startswith("https://play.min.io/"))

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
        result = await self.client.list_buckets()

        self.assertTrue(len(result) > 0)

    async def test_list_objects(self):
        result = await self.client.list_objects(self.bucket_name)

        self.assertTrue(len(result) > 0)

        count = 0
        async for _ in self.client.list_objects(self.bucket_name):
            count += 1

        self.assertTrue(count > 0)

    async def test_get_object(self):
        raw_content = fake.binary(5 * 1024 * 1024)
        await self.put_test_file(content=raw_content)

        response = await self.client.get_object(self.bucket_name, self.test_file_name)
        content = await response.content.read()

        self.assertEqual(content, raw_content)

    async def test_fget_object(self):
        result = await self.client.fget_object(
            self.bucket_name, self.test_file_name, self.test_file_name
        )
        self.addCleanup(os.remove, self.test_file_name)

        self.assertEqual(result.bucket_name, self.bucket_name)
        self.assertEqual(result.object_name, self.test_file_name)
        self.assertEqual(result.size, 5 * 1024 * 1024)

    async def test_select_object_content(self):
        await self.put_test_file(content=fake.text(5).encode())

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


if __name__ == "__main__":
    unittest.main()
