from sanic import Sanic
from sanic.response import redirect
from sanic_jinja2 import SanicJinja2
from minio_async import Minio
import aiofiles
import os
from urllib import parse

app = Sanic(__name__)
template = SanicJinja2(app, pkg_name='run') # pkg_name is the main file name, here is for run.py


def get_client():  # client must be created in async function
    client = Minio(
        endpoint="Your host",
        access_key="Your username",
        secret_key="Your password",
        secure=False  # http for False, https for True
    )
    return client


@app.route('/', methods=['POST', 'GET'])
async def index(request):
    if request.method == 'POST':
        f = request.files.get('file')
        if f:  # if f is not None then the post request is from upload, else is from download
            print('uploading ...')
            save_path = os.path.join('cache', f.name)  # save stream to cache
            async with aiofiles.open(save_path, 'wb') as temp:
                await temp.write(f.body)
            temp.close()

            bucket = request.form.get('bucket')
            client = get_client()
            # upload from cache
            await client.fput_object(bucket_name=bucket, object_name=f.name, file_path=save_path)
            os.remove(save_path)  # clear cache

            return redirect(app.url_for('index'))
        else:  # redirect to download
            bucket = request.form.get('bucket')
            file_name = request.form.get('fileName')
            return redirect(app.url_for('download', bucket=bucket, fileName=file_name))
    return template.render('index.html', request)


@app.route('/download/<bucket>/<fileName>', methods=['GET'])
async def download(request, bucket, fileName):
    print('downloading ...')
    client = get_client()
    fileName = parse.unquote(fileName) # decodeURI, for those which has other language in fileName, such as Chinese, Japanese, Korean
    url = await client.presigned_get_object(bucket_name=bucket, object_name=fileName) # get download url from minio, expiry default to 7 days 
    return redirect(url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
