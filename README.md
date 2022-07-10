# minio-async
> Asynchronous MinIO Python SDK

<br/>

## Dependencies
- Python>3.6

<br/>

## Build from source
Github Repository
```sh
git clone https://github.com/hlf20010508/minio-async.git
cd minio-async
python setup.py install
```

Gitee Repository
```sh
git clone https://gitee.com/hlf01/minio-async.git
cd minio-async
python setup.py install
```

<br/>

## Install with pip
Github Repository
```sh
pip install git+https://github.com/hlf20010508/minio-async.git
```

Gitee Repository
```sh
pip install git+https://gitee.com/hlf01/minio-async.git
```

<br/>

## Install with pipenv
Github Repository
```sh
pipenv install git+https://github.com/hlf20010508/minio-async.git#egg=minio-async
```

Gitee Repository
```sh
pipenv install git+https://gitee.com/hlf01/minio-async.git#egg=minio-async
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

Check more examples in <a href="https://github.com/hlf20010508/minio-async/tree/master/examples">examples</a> on Github and <a href="https://gitee.com/hlf2001/minio-async/tree/master/examples">examples</a> on Gitee

Refer documents in <a href="https://github.com/hlf20010508/minio-async/tree/master/docs">docs</a> on Github and <a href="https://gitee.com/hlf2001/minio-async/tree/master/docs">docs</a> on Gitee

<br/>

## Link
- <a href="https://github.com/hlf20010508/minio-async.git">minio-async</a> on Github
- <a href="https://gitee.com/hlf01/minio-async.git">minio-async</a> on Gitee
