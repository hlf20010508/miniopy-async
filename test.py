#!/usr/bin/python3
import asyncio
import io
from math import tanh
import uvicorn
import minio
import pprint
import json
import datetime
from minio.error import S3Error

from minio.helpers import BytesDataSource, ObjectWriteResult

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response, StreamingResponse, PlainTextResponse
from starlette.requests import Request


async def create_minio_instance():
    app.state.minio = minio.Minio("127.0.0.1:9000", "minioadmin", "minioadmin", secure=False)

async def create_service(request):
    empty_dict = json.dumps({}).encode()
    object = await request.app.state.minio.put_object("metadata", request.path_params['service'], 
                    BytesDataSource(empty_dict), len(empty_dict),
                    content_type="application/json"
                )
    print(object)
    return JSONResponse({"message": f"`{object.object_name}` has been created"})

async def list_services(request):
    services = await request.app.state.minio.list_objects("metadata")
    return JSONResponse([service.object_name for service in services])

async def retrieve_service(request):
    try:
        return JSONResponse(await (await request.app.state.minio.get_object("metadata", request.path_params["service"])).json())
    except S3Error:
        return JSONResponse({"message": "Service `{request.path_params['service']}` not found"})


async def create_config(request):
    tag = request.query_params.get("tag")
    service_name = request.path_params["service"]
    content_length = request.headers.get('content-length')

    if not tag:
        return JSONResponse({"message": "`tag` field is missing"}, 401)
    object_write_result = await request.app.state.minio.put_object("services", f"{service_name}-TAG-{tag}", 
                                        request.stream(), 
                                        int(content_length) if content_length else -1,
                                        )
    
    # Modify metadata file
    metadata: dict = await (await request.app.state.minio.get_object("metadata", service_name)).json()
    tag_data = metadata.get(tag, {})

    if tag_data:
        tag_data["revisions"][object_write_result.version_id] = {"timestamp": str(datetime.datetime.now())}
    else:
        tag_data["revisions"] = {object_write_result.version_id: {"timestamp": str(datetime.datetime.now())}}
    tag_data["current"] = object_write_result.version_id
    metadata[tag] = tag_data
    metadata_bytes = json.dumps(metadata).encode()

    await request.app.state.minio.put_object("metadata", service_name, 
                                        BytesDataSource(metadata_bytes), len(metadata_bytes),
                                        content_type="application/json")
    return JSONResponse("", status_code=201)

async def retrieve_config(request: Request) -> Response:
    tag = request.query_params.get('tag')
    service_name = request.path_params["service"]

    if not tag:
        return JSONResponse({"message": "`tag` field is missing"}, 401)
    
    object = await request.app.state.minio.get_object("services", f"{service_name}-TAG-{tag}", 
                                    version_id=request.query_params.get("version-id"))
    print("ETag: ", object.headers.get("ETag"))
    return StreamingResponse(object.content.iter_any(), headers={"ETag": object.headers.get("ETag")})

async def delete_config(request: Request) -> Response:
    tag = request.query_params.get('tag')
    service_name = request.path_params["service"]

    if not tag:
        return JSONResponse({"message": "`tag` field is missing"}, 401)
     
    try:
         service_metadata = await (await request.app.state.minio.get_object("metadata", service_name)).json()
         if tag_data := service_metadata.get("tag"):
             pass
    except S3Error:
        pass
routes = [
    Route("/services/{service}", create_service, methods=["POST"]),
    Route("/services/", list_services, methods=["GET"]),
    Route("/services/{service}", retrieve_service, methods=["GET"]),

    Route("/services/{service}/config", create_config, methods=["POST"]),
    Route("/services/{service}/config", retrieve_config, methods=["GET"]),
    Route("/services/{service}/config", delete_config, methods=["DELETE"]),
]

app = Starlette(debug=True, routes=routes, on_startup=[create_minio_instance], on_shutdown=[])

if __name__ == "__main__":
    uvicorn.run(app)
