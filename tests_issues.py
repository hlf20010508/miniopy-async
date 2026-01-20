import asyncio
import unittest
import warnings
from io import BytesIO
from typing import cast

from faker import Faker

from miniopy_async import Minio
from miniopy_async.deleteobjects import DeleteObject

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
        self.client._ensure_session()  # pyright: ignore[reportPrivateUsage]

    async def asyncTearDown(self):
        await self.client.close_session()
        await asyncio.sleep(5)

    @classmethod
    def tearDownClass(cls):
        async def remove_bucket():
            cls.client._ensure_session()  # pyright: ignore[reportPrivateUsage]
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

    async def test_unsafe_object_name(self):
        # https://github.com/hlf20010508/miniopy-async/issues/52
        object_name = "sales&marketing.csv"
        content = b"hello"

        await self.put_test_file(filename=object_name, content=content)

        stat = await self.client.stat_object(self.bucket_name, object_name)
        self.assertEqual(stat.bucket_name, self.bucket_name)
        self.assertEqual(stat.object_name, object_name)


if __name__ == "__main__":
    unittest.main()
