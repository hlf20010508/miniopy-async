# miniopy-async
> Asynchronous MinIO Client SDK for Python

[![PyPI](https://img.shields.io/pypi/v/miniopy-async)](https://pypi.org/project/miniopy-async/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/miniopy-async)](https://pypi.org/project/miniopy-async/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/miniopy-async)](https://pypi.org/project/miniopy-async/)  
[![GitHub repo size](https://img.shields.io/github/repo-size/hlf20010508/miniopy-async)](https://github.com/hlf20010508/miniopy-async)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/hlf20010508/miniopy-async/python-publish.yml)](https://github.com/hlf20010508/miniopy-async/actions)
[![GitHub closed issues](https://img.shields.io/github/issues-closed/hlf20010508/miniopy-async)](https://github.com/hlf20010508/miniopy-async/issues?q=is%3Aissue+is%3Aclosed)
[![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/hlf20010508/miniopy-async)](https://github.com/hlf20010508/miniopy-async/pulls?q=is%3Apr+is%3Aclosed)

## Catalogue
- [Declaration](#declaration)
- [Minimum Requirements](#requirements)
- [Build from source](#build)
- [Installation](#installation)
- [Quick Start](#example)
- [More References](#references)

<span id="declaration"></span>

## Declaration
- This project is based on Huseyn Mashadiyev's [minio-async](https://github.com/HuseynMashadiyev/minio-async/tree/78128443f7ce9618191e1155689b47507df67bb1) 1.0.0.
- This project has fixed some bugs of minio-async and added some new features.
- Miniopy-async 1.2 has been pulled requests to minio-async.

<span id="requirements"></span>

## Minimum Requirements
- Python>3.6

<span id="build"></span>

## Build from source
```sh
git clone https://github.com/hlf20010508/miniopy-async.git
cd miniopy-async
python setup.py install
```

<span id="installation"></span>

## Installation
### Install with pip
PyPI
```sh
pip install miniopy-async
```

Github Repository
```sh
pip install git+https://github.com/hlf20010508/miniopy-async.git
```

### Install with pipenv
PyPI
```sh
pipenv install miniopy-async
```

Github Repository
```sh
pipenv install "miniopy-async@ git+https://github.com/hlf20010508/miniopy-async.git"
```

<span id="example"></span>

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


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
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

<span id="references"></span>

## More References
- <a href="https://github.com/hlf20010508/miniopy-async/tree/master/docs">Python Client API Reference</a>  
- <a href="https://github.com/hlf20010508/miniopy-async/tree/master/examples">Examples</a>
