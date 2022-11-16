import asyncio

import aiohttp
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from miniopy_async.api import _attach_finalizer


class AioUtilsTest(AioHTTPTestCase):

    async def get_application(self):
        async def mock_get(request):
            return web.Response(body=b''.join(bytes(i) for i in range(10240)))

        app = web.Application()
        app.router.add_get('/mock-get', mock_get)
        return app

    async def testClientSessionFinalizers(self):
        session = aiohttp.ClientSession()
        response = await session.get(self.client.make_url('/mock-get'))
        connector = session.connector

        _attach_finalizer(response, session, self.loop)
        response.close()  # Can also call `response.read()`. This is needed to GC the response object
        self.assertFalse(connector.closed)
        del response, session
        await asyncio.sleep(1)

        self.assertTrue(connector.closed)
