# miniopy-async
[![PyPI](https://img.shields.io/pypi/v/miniopy-async)](https://pypi.org/project/miniopy-async/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/miniopy-async)](https://pypi.org/project/miniopy-async/) 
[![PyPI - Downloads](https://img.shields.io/pypi/dm/miniopy-async)](https://pypi.org/project/miniopy-async/) 

Asynchronous MinIO Client SDK for Python

- Document: https://hlf20010508.github.io/miniopy-async/
- Examples: https://github.com/hlf20010508/miniopy-async/tree/master/examples

## Build from Source
```sh
git clone https://github.com/hlf20010508/miniopy-async.git
cd miniopy-async
poetry install
poetry build
```

## Installation
PyPI
```sh
pip install miniopy-async
```

Github Repository
```sh
pip install git+https://github.com/hlf20010508/miniopy-async.git
```

## Quick Start
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
    url = await client.presigned_get_object("my-bucket", "my-object")
    print('url:', url)


asyncio.run(main())
```

```py
from sanic import Sanic, response
from miniopy_async import Minio
from urllib import parse

app = Sanic(__name__)

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)


# http://127.0.0.1:8000/download?bucket=my-bucket&fileName=testfile
@app.route('/download', methods=['GET'])
async def download(request):
    print('downloading ...')
    bucket=request.args.get('bucket')
    fileName=request.args.get('fileName')

    # decodeURI, for those which has other language in fileName, such as Chinese, Japanese, Korean
    fileName = parse.unquote(fileName)

    url = await client.presigned_get_object(bucket_name=bucket, object_name=fileName)
    return response.redirect(url)
```
