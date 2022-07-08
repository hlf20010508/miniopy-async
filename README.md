# minio-async
> Async version of minio python API

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

### Simple Example
```python
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
```

If you're using some async frame or module, you have to create the client object in its async function.
```python
from sanic import Sanic

app = Sanic(__name__)

def get_client():
    client = Minio(
        endpoint="Your host",
        access_key="Your username",
        secret_key="Your password",
        secure=False  # http for False, https for True
    )
    return client


@app.route('/download', methods=['GET'])
async def download(request):
    print('downloading ...')
    bucket=request.form.get('bucket')
    fileName=request.form.get('fileName')

    # decodeURI, for those which has other language in fileName, such as Chinese, Japanese, Korean
    fileName = parse.unquote(fileName)

    client = get_client() # create client here in a async function
    url = await client.presigned_get_object(bucket_name=bucket, object_name=fileName)
    return redirect(url)
```

Check more example in <a href="https://github.com/hlf20010508/minio-async/tree/master/example">example</a>

<br/>

## Link
- <a href="https://github.com/hlf20010508/minio-async.git">minio-async</a> on Github
- <a href="https://gitee.com/hlf01/minio-async.git">minio-async</a> on Gitee
