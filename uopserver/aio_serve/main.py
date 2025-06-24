import base64, sys
from cryptography import fernet
from aiohttp import web
from aiohttp_session import setup, get_session, session_middleware
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from uopserver.aio_serve.views import routes, base_context
from uop import db_service
import aiohttp_cors
import logging
import argparse

logger = logging.getLogger()


async def handler(request):
    session = await get_session(request)
    last_visit = session['last_visit'] if 'last_visit' in session else None
    text = 'Last visited: {}'.format(last_visit)
    return web.Response(text=text)

async def make_app():
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    # secret_key must be 32 url-safe base64-encoded bytes
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    setup(app, EncryptedCookieStorage(secret_key))
    app.add_routes(routes)
    # app.router.add_static('/', path='/var/www/pkm/', name='static2')

    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)
    logging.basicConfig(level=logging.DEBUG)
    return app


def main():
    app = make_app()
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--dbType', type=str, help='type of database', default='mongo')
    parser.add_argument('-d', '--dbName', type=str, help='name of database', default='pkm_app')
    parser.add_argument('-H', '--dbHost', type=str, help='host of database', default='localhost')
    options = parser.parse_args(sys.argv[1:])
    print('current options', options)
    base_context['service'] = db_service.get_service(options.dbType, use_async=True, host=options.dbHost, db_name=options.dbName)
    web.run_app(app, host='0.0.0.0', access_log_format=" :: %r %s %T %t")


main()
