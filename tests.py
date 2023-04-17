from miniopy_async import Minio
from miniopy_async.commonconfig import ComposeSource, CopySource
import asyncio
import os

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

bucket_name = 'my-bucket'
test_file_name = ['testfile-1', 'testfile-2']
sources = [
    ComposeSource("my-bucket", file_name) for file_name in test_file_name
]
test_content = b'1' * 1024 * 1024 * 5  # 5MB

async def create_bucket():
    if not await client.bucket_exists(bucket_name):
        await client.make_bucket(bucket_name)
        print('Created bucket %s'%bucket_name)
    else:
        print('Bucket %s exists'%bucket_name)

async def put_object():
    for file_name in test_file_name:
        with open(file_name, 'wb') as file:
            file.write(test_content)
        await client.fput_object(bucket_name, file_name, file_name)
        os.remove(file_name)
    print('Uploaded test file')

async def compose_object():
    result = await client.compose_object(bucket_name, "composed-object", sources)
    print(result.object_name, result.version_id)

async def copy_object():
    result = await client.copy_object(
        bucket_name,
        "copied-object",
        CopySource(bucket_name, test_file_name[0]),
    )
    print(result.object_name, result.version_id)

async def get_object():
    await client.fget_object(bucket_name, test_file_name[0], 'testfile')

async def main():
    print('Testing create bucket...')
    await create_bucket()
    print('Testing put object...')
    await put_object()
    print('Testing compose object..')
    await compose_object()
    print('Testing copy object')
    await copy_object()
    print('Testing get object...')
    await get_object()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
