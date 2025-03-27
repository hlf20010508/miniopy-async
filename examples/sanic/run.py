# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
# (C) 2022 L-ING <hlf01@icloud.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from sanic import Sanic
from sanic.response import redirect
from sanic_jinja2 import SanicJinja2
from miniopy_async import Minio
import aiofile
import os
from urllib import parse

app = Sanic(__name__)
template = SanicJinja2(
    app, pkg_name="run"
)  # pkg_name is the main file name, here is for run.py


client = Minio(
    "play.min.io",
    access_key="Q3AM3UQ867SPQQA43P2F",
    secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
    secure=True,  # http for False, https for True
)


@app.route("/", methods=["POST", "GET"])
async def index(request):
    if request.method == "POST":
        f = request.files.get("file")
        if (
            f
        ):  # if f is not None then the post request is from upload, else is from download
            print("uploading ...")
            save_path = os.path.join("cache", f.name)  # save stream to cache
            async with aiofile.open(save_path, "wb") as temp:
                await temp.write(f.body)
            temp.close()

            bucket = request.form.get("bucket")
            # upload from cache
            await client.fput_object(
                bucket_name=bucket, object_name=f.name, file_path=save_path
            )
            os.remove(save_path)  # clear cache

            return redirect(app.url_for("index"))
        else:  # redirect to download
            bucket = request.form.get("bucket")
            file_name = request.form.get("fileName")
            return redirect(app.url_for("download", bucket=bucket, fileName=file_name))
    return template.render("index.html", request)


@app.route("/download/<bucket>/<fileName>", methods=["GET"])
async def download(request, bucket, fileName):
    print("downloading ...")
    fileName = parse.unquote(
        fileName
    )  # decodeURI, for those which has other language in fileName, such as Chinese, Japanese, Korean
    url = await client.presigned_get_object(
        bucket_name=bucket, object_name=fileName
    )  # get download url from minio, expiry default to 7 days
    return redirect(url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
