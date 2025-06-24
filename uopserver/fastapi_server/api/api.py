from fastapi import APIRouter
from uopserver.fastapi_server.api.endpoints import service



api_router = APIRouter()

api_router.include_router(service.router, prefix='uop', tags=['UOP'])