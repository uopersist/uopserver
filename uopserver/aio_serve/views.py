from aiohttp import web
from functools import wraps
import asyncio
from aiohttp_session import get_session
from uop import changeset

dbi_map = {}
routes = web.RouteTableDef()

base_context = {'service': None}
tenant_service = {}

thoughts = '''

On RestFul and other API

In a way many of the http APIs are highly redundant as all APIs
that mutate can be subsumed by posting changes from clients.  Indeed
the underlying backend functions produce or add to changesets and 
optionally apply them.  

So a handful of GET methods, POSTS of changes and query processing 
are sufficient for a changeset based front end.  This minimal set
forms the critical kernel. 
'''


async def current_service(request):
    tenant = await current_tenant(request)
    base_service = base_context['service']
    if tenant:
        key = tenant
        if not tenant_service.get(key):
            tenant_service[key] = base_service
        return tenant_service[key]
    return base_service


async def current_tenant(request):
    session = await get_session(request)
    return session.get('tenant_id') if session else None


async def get_dbi(request):
    tenant = await current_tenant(request)
    return dbi_map[tenant]


def multi_item(seq):
    return dict(count=len(seq), results=list(seq))


def authorized():
    def outer(fn):
        @wraps(fn)
        async def inner(request):
            tenant = await current_tenant(request)
            if tenant:
                return await fn(request)
            else:
                return web.json_response({}, reason='not logged in', status=401)

        return inner

    return outer


def admin_only():
    def outer(fn):
        @wraps(fn)
        async def inner(request):
            session = await get_session(request)
            if session and session.get('is_admin'):
                return await fn(request)
            else:
                return web.json_response({}, reason='requires admin', status=401)

        return inner

    return outer


@routes.get('/login')
async def is_logged_in(request):
    session = await get_session(request)
    res = {'logged_in': bool(session and session.get('tenant_id'))}
    if res['logged_in']:
        res['isAdmin'] = session.get('isAdmin')
        service = await current_service(request)
        res['tenant'] = await service.get_tenant(session.get('tenant_id'))
    return web.json_response(res)


@routes.post('/login')
async def login(request):
    data = await request.json()
    service = await current_service(request)
    tenant = await service.login_tenant(**data)
    if tenant:
        tenant.pop('password', None)
        session = await get_session(request)
        session['tenant_id'] = tenant['_id']
        session['isAdmin'] = bool(tenant.get('isAdmin'))
        dbi_map[tenant['_id']] = await service.tenant_interface(tenant['_id'])

        return web.json_response(tenant)


# @routes.get('/')
# async def index(request):
#   return web.FileResponse('/var/www/pkm/index.html')

@routes.post('/logout')
async def logout(request):
    session = await get_session(request)
    session.pop('tenant_id', None)
    return web.json_response({})


@routes.get('/metadata')
@authorized()
async def get_metadata(request):
    dbi = await get_dbi(request)
    print(dbi)
    meta = await dbi.metadata()
    return web.json_response(meta._by_id)


@routes.get('/tenants')
@admin_only()
async def get_tenants(request):
    service = await current_service(request)

    data = await service.tenants()
    return web.json_response(data)


@routes.delete('/tenants/{tenant_id}')
@authorized()
async def drop_tenant(request):
    dbi = await get_dbi(request)
    uid = request.match_info['tenant_id']
    service = await current_service(request)

    await service.drop_tenant(uid)
    return web.json_response({})


@routes.post('/register')
@admin_only()
async def register(request):
    data = await request.json()
    service = await current_service(request)

    return web.json_response(await service.register(**data))


@routes.post('/object-string')
@authorized()
async def object_from_string(request):
    dbi = await get_dbi(request)
    data = await request.json()
    res = await dbi.get_by_objectRef(data['objectRef'], recordNew=False)
    return web.json_response(res)


@routes.get('/changes/{until}')
@authorized()
async def changes_since(request):
    dbi = await get_dbi(request)
    until = request.match_info['until']
    changes = await dbi.changes_until(until)
    data = changes.to_dict()
    return web.json_response(data)


@routes.post('/changes')
@authorized()
async def apply_changes(request):
    dbi = await get_dbi(request)
    tenant = await current_tenant(request)
    service = await current_service(request)

    changes = await request.json()
    changes = changeset.ChangeSet(**changes)
    await dbi.apply_changes(changes)
    await service.update_if_app_changes(tenant, changes)
    return web.json_response({})


@routes.get('/objects/{object_id}')
@authorized()
async def get_object(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    return web.json_response(await dbi.get_object(oid))


@routes.put('/object-groups/{object_id}')
@authorized()
async def modify_object_groups(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    groups = await request.json()
    await asyncio.gather([dbi.group(oid, gid) for gid in groups])


@routes.post('/object-groups/{object_id}')
@authorized()
async def set_object_groups(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    groups = await request.json()
    await dbi.set_object_groups(oid, groups)


@routes.post('/object-groups/{object_id}/{group_id}')
@authorized()
async def group_object(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    group_id = request.match_info['group_id']
    await dbi.group(oid, group_id)


@routes.get('/object-groups/{object_id}')
@authorized()
async def get_object_groups(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    return web.json_response(multi_item(await dbi.get_object_groups(oid)))


@routes.put('/object-tags/{object_id}')
@authorized()
async def modify_object_tags(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    tags = await request.json()
    await asyncio.gather([dbi.tag(oid, gid) for gid in tags])


@routes.post('/object-tags/{object_id}')
@authorized()
async def set_object_tags(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    tags = await request.json()
    await dbi.set_object_tags(oid, tags)


@routes.post('/object-tags/{object_id}/{tag_id}')
@authorized()
async def tag_object(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    tag_id = request.match_info['tag_id']
    await dbi.tag(oid, tag_id)


@routes.get('/object-tags/{object_id}')
@authorized()
async def get_object_tags(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    return web.json_response(multi_item(await dbi.get_object_tags(oid)))


@routes.get('/object-roles/{object_id}')
@authorized()
async def get_object_roles(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    return web.json_response(multi_item(await dbi.get_object_roles(oid)))


@routes.get('/tag-neighbors/{object_id}')
@authorized()
async def tag_neighbors(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    res = await dbi.tag_neighbors(oid)
    return web.json_response(res)


@routes.get('/group-neighbors/{object_id}')
@authorized()
async def group_neighbors(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    res = await dbi.group_neighbors(oid)
    return web.json_response(res)


@routes.get('/role-neighbors/{object_id}')
@authorized()
async def tag_neighbors(request):
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    return web.json_response(await dbi.get_object_relationships(oid))


@routes.get('/related-objects/{object_id}/{role_id}')
@authorized()
async def related_to_object(request):
    '''
    Returns the ids of objects related to the specified object by
    the specified role
    :param request:
    :return:
    '''
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    role = request.match_info['role_id']
    return web.json_response(await dbi.get_roleset(oid, role))


@routes.put('/related-objects/{object_id}/{role_id}')
@authorized()
async def add_related_objects(request):
    '''
    relate an object via a specified role to one or more objects
    :param request:
    :return:
    '''
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    role = request.match_info['role_id']
    objects = await request.json()
    await dbi.add_object_related(oid, role, objects)


@routes.post('/related-objects/{object_id}/{role_id}')
@authorized()
async def set_related_objects(request):
    '''
    specify the set of objects related to the give object by
    the given role
    :param request:
    :return:
    '''
    dbi = await get_dbi(request)
    oid = request.match_info['object_id']
    role = request.match_info['role_id']
    objects = await request.json()
    await dbi.set_object_related(oid, role, objects)


@routes.get('/tagged/{tag_id}')
@authorized()
async def get_tagged(request):
    dbi = await get_dbi(request)
    tag_id = request.match_info['tag_id']
    res = list(await dbi.get_tagset(tag_id))
    return web.json_response(res)


@routes.put('/tagged/{tag_id}')
@authorized()
async def add_tagged(request):
    dbi = await get_dbi(request)
    tag_id = request.match_info['tag_id']
    objects = await request.json()
    await dbi.add_tag_objects(tag_id, object_ids=objects)


@routes.post('/tagged/{tag_id}')
@authorized()
async def set_tagged(request):
    dbi = await get_dbi(request)
    tag_id = request.match_info['tag_id']
    objects = await request.json()
    await dbi.set_tag_objects(tag_id, object_ids=objects)


@routes.get('/groupged/{group_id}')
@authorized()
async def get_groupged(request):
    dbi = await get_dbi(request)
    group_id = request.match_info['group_id']
    return web.json_response(list(await dbi.get_groupset(group_id)))


@routes.put('/groupged/{group_id}')
@authorized()
async def add_groupged(request):
    dbi = await get_dbi(request)
    group_id = request.match_info['group_id']
    objects = await request.json()
    await dbi.add_group_objects(group_id, object_ids=objects)


@routes.post('/groupged/{group_id}')
@authorized()
async def set_groupged(request):
    dbi = await get_dbi(request)
    group_id = request.match_info['group_id']
    objects = await request.json()
    await dbi.set_group_objects(group_id, object_ids=objects)


@routes.get('/tags')
@authorized()
async def get_tags(request):
    dbi = await get_dbi(request)
    return web.json_response(list(await dbi.tags.find()))


@routes.post('/tags')
@authorized()
async def create_tag(request):
    dbi = await get_dbi(request)
    data = await request.json()
    dbi.add_tag(**data)


@routes.put('/tags/{tag_id}')
@authorized()
async def modify_tag(request):
    dbi = await get_dbi(request)
    tag_id = request.match_info['tag_id']
    data = await request.json()
    data.pop('_id', None)  # avoid possible change of this
    return await dbi.modify_tag(tag_id, **data)


@routes.delete('/tags/{tag_id}')
@authorized()
async def modify_tag(request):
    dbi = await get_dbi(request)
    tag_id = request.match_info['tag_id']
    await dbi.delete_tag(tag_id)


@routes.get('/attributes')
@authorized()
async def get_attributes(request):
    dbi = await get_dbi(request)
    return web.json_response(list(await dbi.attributes.find()))


@routes.post('/attributes')
@authorized()
async def create_attribute(request):
    dbi = await get_dbi(request)
    data = await request.json()
    await dbi.add_attribute(**data)


@routes.post('/bulk-load')
@authorized()
async def bulk_load(request):
    dbi = await get_dbi(request)
    data = await request.json()
    res = await dbi.bulk_load(data['ids'])
    return web.json_response(multi_item(res))


@routes.put('/attributes/{attribute_id}')
@authorized()
async def modify_attribute(request):
    dbi = await get_dbi(request)
    attribute_id = request.match_info['attribute_id']
    data = await request.json()
    data.pop('_id', None)  # avoid possible change of this
    return await dbi.modify_attribute(attribute_id, **data)


@routes.delete('/attributes/{attribute_id}')
@authorized()
async def delete_attribute(request):
    dbi = await get_dbi(request)
    attribute_id = request.match_info['attribute_id']
    await dbi.delete_attribute(attribute_id)


@routes.get('/groups')
@authorized()
async def get_groups(request):
    dbi = await get_dbi(request)
    return web.json_response(list(await dbi.groups.find()))


@routes.post('/groups')
@authorized()
async def create_group(request):
    dbi = await get_dbi(request)
    data = await request.json()
    dbi.add_group(**data)


@routes.put('/groups/{group_id}')
@authorized()
async def modify_group(request):
    dbi = await get_dbi(request)
    group_id = request.match_info['group_id']
    data = await request.json()
    data.pop('_id', None)  # avoid possible change of this
    return await dbi.modify_group(group_id, **data)


@routes.delete('/groups/{group_id}')
@authorized()
async def delete_group(request):
    dbi = await get_dbi(request)
    group_id = request.match_info['group_id']
    await dbi.delete_group(group_id)


@routes.get('/roles')
@authorized()
async def get_roles(request):
    dbi = await get_dbi(request)
    return web.json_response(list(await dbi.roles.find()))


@routes.post('/roles')
@authorized()
async def create_role(request):
    dbi = await get_dbi(request)
    data = await request.json()
    dbi.add_role(**data)


@routes.put('/roles/{role_id}')
@authorized()
async def modify_role(request):
    dbi = await get_dbi(request)
    role_id = request.match_info['role_id']
    data = await request.json()
    data.pop('_id', None)  # avoid possible change of this
    return await dbi.modify_role(role_id, **data)


@routes.delete('/roles/{role_id}')
@authorized()
async def delete_role(request):
    dbi = await get_dbi(request)
    role_id = request.match_info['role_id']
    await dbi.delete_role(role_id)


@routes.get('/classes')
@authorized()
async def get_classes(request):
    dbi = await get_dbi(request)
    return web.json_response(await dbi.classes.find())


@routes.post('/classes')
@authorized()
async def create_class(request):
    dbi = await get_dbi(request)
    data = await request.json()
    dbi.add_class(**data)


@routes.put('/classes/{class_id}')
@authorized()
async def modify_class(request):
    dbi = await get_dbi(request)
    class_id = request.match_info['class_id']
    data = await request.json()
    data.pop('_id', None)  # avoid possible change of this
    return await dbi.modify_class(class_id, **data)


@routes.delete('/classes/{class_id}')
@authorized()
async def delete_class(request):
    dbi = await get_dbi(request)
    class_id = request.match_info['class_id']
    await dbi.delete_class(class_id)


@routes.get('/queries')
@authorized()
async def get_queries(request):
    dbi = await get_dbi(request)
    return web.json_response(list(await dbi.queries.find()))


@routes.post('/queries')
@authorized()
async def create_query(request):
    dbi = await get_dbi(request)
    data = await request.json()
    dbi.add_query(**data)


@routes.put('/queries/{query_id}')
@authorized()
async def modify_query(request):
    dbi = await get_dbi(request)
    query_id = request.match_info['query_id']
    data = await request.json()
    data.pop('_id', None)  # avoid possible change of this
    return await dbi.modify_query(query_id, **data)


@routes.delete('/queries/{query_id}')
@authorized()
async def delete_query(request):
    dbi = await get_dbi(request)
    query_id = request.match_info['query_id']
    await dbi.delete_query(query_id)


@routes.post('/run-query/{query_id}')
@routes.post('/run-query')
@authorized()
async def run_query(request):
    dbi = await get_dbi(request)
    query_id = request.match_info.get('query_id')
    print('query_id', query_id)
    if query_id:
        query = await dbi.queries.get(query_id)
    else:
        query = await request.json()

    result = await dbi.query(query)
    return web.json_response(multi_item(result))


@routes.get('/{tail:.*}')
async def index_default(request):
    return web.FileResponse('/var/www/pkm/index.html')
