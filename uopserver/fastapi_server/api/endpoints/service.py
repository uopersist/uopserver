from uop import db_service
from fastapi import APIRouter, Header, Request
from typing import Optional

routes = APIRouter()

def get_dbi(request:Request):
    dbi = None
    return dbi

@routes.get('/changes/{since}')
async def get_changeset(request: Request, since=None):
    dbi = get_dbi(request)
    data = dbi.changes_since(since)
    return data

@routes.post('/changes')
async def apply_changes(changes: dict):
    dbi.apply_changes(changes)


@routes.get('/metadata')
async def get_metadata(request:Request):
    return dbi.metadata

@routes.get('/tenants')
async def get_tenants():
    return dbi.

