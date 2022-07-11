# miniopy-async
> Asynchronous MinIO Python Client API

## Declaration
This project based on Huseyn Mashadiyev's minio-async 1.0.0

<br/>

## Dependencies
- Python>3.6

<br/>

## Build from source
```sh
git clone -b miniopy-async https://github.com/hlf20010508/minio-async.git
cd minio-async
python setup.py install
```

<br/>

## Install with pip

PyPI
```sh
pip install miniopy-async
```

Github Repository
```sh
pip install git+https://github.com/hlf20010508/minio-async.git@miniopy-async
```

<br/>

## Install with pipenv

PyPI
```sh
pipenv install miniopy-async
```

Github Repository
```sh
pipenv install git+https://github.com/hlf20010508/minio-async.git@miniopy-async#egg=minio-async
```

<br/>

## Usage
```python
import minio_async
```

### Examples
```python
from minio_async import Minio
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
from minio_async import Minio

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

Check more examples in <a href="https://github.com/hlf20010508/minio-async/tree/miniopy-async/examples">examples</a>

Refer documents in <a href="https://github.com/hlf20010508/minio-async/tree/miniopy-async/docs">docs</a>

<br/>

## Link
- <a href="https://pypi.org/project/miniopy-async/">miniopy-async</a> on PyPI
- <a href="https://github.com/hlf20010508/minio-async/tree/miniopy-async">miniopy-async</a> on Github
