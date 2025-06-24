
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.api.api_v1.api import api_router
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from app.exceptions.request import request_exception_handler


#Base.metadata.create_all(bind=engine)
API_V1_STR='/api/v1'
app = FastAPI(
    title='Perilous Realms', openapi_url=f"{API_V1_STR}/openapi.json"
)

# load env variables from .env file
#load_dotenv(find_dotenv())

BACKEND_CORS_ORIGINS = []
# Set all CORS enabled origins
if BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in []],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=API_V1_STR)
app.add_exception_handler(RequestValidationError, request_exception_handler)


@app.middleware('http')
async def add_access_log(request: Request, call_next):
    response = await call_next(request)
    print(f'{request.method} {request.url.path} - {response.status_code}')
    print(f'Request headers: {request.headers}')
    return response

def custom_openapi():
    # https://fastapi.tiangolo.com/tutorial/path-params/#openapi-support
    try:
        # print(f"In custom_openapi {os.environ}")
        openapi_schema = get_openapi(
            title='PRServer',
            version=API_V1_STR,
            description="Perilous Realms Game",
            openapi_version="3.0.0",
            routes=app.routes,
        )

        app.openapi_schema = openapi_schema
    except Exception as e:
        print(f"Exception in custom_openapi: {str(e)}")
    return app.openapi_schema


app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    import os
    port = 8080
    uvicorn.run(app, host="0.0.0.0", port=port)
