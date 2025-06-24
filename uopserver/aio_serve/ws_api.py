import asyncio
import websockets

dbi_map = {}


async def echo(websocket, path):
    async for message in websocket:
        response = await exec_message(message)
        await websocket.send(response)


async def exec_message(message):
    cli


async def metadata(client_id)
    dbi = dbi_map.get(client_id)
    return (await dbi.metadata())._by_id


asyncio.get_event_loop().run_until_complete(
    websockets.serve(echo, 'localhost', 8765))
asyncio.get_event_loop().run_forever()
