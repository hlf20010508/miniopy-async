from minio_async import Minio
import asyncio

client = Minio(
    endpoint="Your host",
    access_key="Your username",
    secret_key="Your password",
    secure=False  # http for False, https for True
)

loop = asyncio.get_event_loop()
res = loop.run_until_complete(client.presigned_get_object("Your bucket name", "Your object name"))
print('Got presigned url:', res)
loop.close()