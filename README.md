# miniopy-async
> Asynchronous MinIO Python Client API

<br/>

## Catalogue
- [Declaration](#declaration)
- [Dependencies](#dependencies)
- [Build from source](#build)
- [Install](#install)
    - [Install with pip](#pip)
    - [Install with pipenv](#pipenv)
- [Usage](#usage)
    - [Examples](#examples)
- [Link](#link)

<br/>

<span id="declaration"></span>

## Declaration
- This project is based on Huseyn Mashadiyev's [minio-async](https://github.com/HuseynMashadiyev/minio-async/tree/78128443f7ce9618191e1155689b47507df67bb1) 1.0.0.
- This project has fixed some bugs of minio-async and added some new functions.
- Miniopy-async 1.2 has been pulled request to minio-async.

<br/>

<span id="dependencies"></span>

## Dependencies
- Python>3.6

<br/>

<span id="build"></span>

## Build from source
```sh
git clone https://github.com/hlf20010508/miniopy-async.git
cd miniopy-async
python setup.py install
```

<br/>

<span id="install"></span>

## Install

<span id="pip"></span>

### Install with pip

PyPI
```sh
pip install miniopy-async
```

Github Repository
```sh
pip install git+https://github.com/hlf20010508/miniopy-async.git
```

<span id="pipenv"></span>

### Install with pipenv

PyPI
```sh
pipenv install miniopy-async
```

Github Repository
```sh
pipenv install git+https://github.com/hlf20010508/miniopy-async.git#egg=miniopy-async
```

<br/>

<span id="usage"></span>

## Usage
```python
import miniopy_async
```

<span id="examples"></span>

### Examples
```python
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

```python
from sanic import Sanic
from miniopy_async import Minio

app = Sanic(__name__)

client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True  # http for False, https for True
)

@app.route('/download', methods=['GET'])
async def download(request):
    print('downloading ...')
    bucket=request.form.get('bucket')
    fileName=request.form.get('fileName')

    # decodeURI, for those which has other language in fileName, such as Chinese, Japanese, Korean
    fileName = parse.unquote(fileName)

    url = await client.presigned_get_object(bucket_name=bucket, object_name=fileName)
    return redirect(url)
```

Check more examples in <a href="https://github.com/hlf20010508/miniopy-async/tree/master/examples">examples</a>

Refer documents in <a href="https://github.com/hlf20010508/miniopy-async/tree/master/docs">docs</a>

<br/>

<span id="link"></span>

## Link
- <a href="https://pypi.org/project/miniopy-async/">miniopy-async</a> on PyPI
- <a href="https://github.com/hlf20010508/miniopy-async">miniopy-async</a> on Github
