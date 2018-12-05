import asyncio
from aiohttp import web, WSMsgType

import settings
from game import Game
from utils import get_client_address, validate_settings, validate_player_name, validate_player_id
from messaging import json, Messaging
from exceptions import ValidationError


def _get_new_player_info(data):
    try:
        player_name = data[1]
    except IndexError:
        raise ValidationError('Missing player name.')
    else:
        player_name = validate_player_name(player_name)

    try:
        player_id = data[2]
    except IndexError:
        player_id = None
    else:
        if player_id:
            player_id = validate_player_id(player_id)
        else:
            player_id = None

    return player_name, player_id


async def ws_handler(request):
    client_address = get_client_address(request)
    game = request.app['game']
    player = None
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
            except ValueError:
                continue

            if isinstance(data, int) and player:
                player.keypress(data)
            elif not isinstance(data, list) or not data:
                continue
            elif data[0] == Messaging.MSG_PING:
                await ws.send_json([Messaging.MSG_PONG] + data[1:], dumps=json.dumps)
            elif data[0] == Messaging.MSG_NEW_PLAYER:
                if not player:
                    try:
                        player_name, player_id = _get_new_player_info(data)
                    except ValidationError as exc:
                        await ws.send_json([Messaging.MSG_ERROR, str(exc)])
                        break
                    else:
                        player = await game.new_player(player_name, ws, player_id=player_id)
            elif data[0] == Messaging.MSG_JOIN:
                if not game.running:
                    await game.reset_world()
                    try:
                        asyncio.ensure_future(game_loop(game))
                    except asyncio.CancelledError:
                        pass

                await game.join(player)

        elif msg.type == WSMsgType.CLOSE:
            break

    if player:
        await game.player_disconnected(player)

    return ws


async def game_loop(game):
    server_shutdown = False
    game.running = True
    game_sleep = 1.0 / game.speed
    game_speed_max = settings.GAME_SPEED_MAX
    game_speed_increase = settings.GAME_SPEED_INCREASE
    game_speed_increase_rate = settings.GAME_SPEED_INCREASE_RATE
    game_frames_max = settings.GAME_FRAMES_MAX
    game_sync_players = settings.GAME_START_WAIT_FOR_PLAYERS

    try:
        if game_sync_players and game.frame == 0:

            while game.players_alive_count < game_sync_players:
                await asyncio.sleep(0.5)

        while True:
            await game.next_frame()

            if not game.players_alive_count:
                break

            if game_frames_max and game.frame >= game_frames_max:
                await game.kill_all()
                if settings.GAME_SHUTDOWN_ON_FRAMES_MAX:
                    await game.shutdown(message='Server shutdown because frames limit reached')
                    server_shutdown = True
                    break

            if (game_speed_increase and game_speed_increase <= game.frame and
                    (not game_speed_max or game.speed < game_speed_max)):
                game.speed = round(game.speed + game.speed * game_speed_increase_rate, 6)
                game_sleep = 1.0 / game.speed

            await asyncio.sleep(game_sleep)

            await game.disconnect_closed()
    except BaseException as exc:
        await game.send_error_all("Internal server error: %s" % exc)
        raise
    finally:
        game.running = False

    if server_shutdown:
        import os
        import signal
        os.kill(os.getpid(), signal.SIGTERM)


async def on_shutdown(app):
    game = app.get('game', None)

    if game:
        await game.shutdown()


def run(host=settings.SERVER_HOST, port=settings.SERVER_PORT):
    validate_settings(settings)

    app = web.Application()
    app['game'] = Game()

    app.router.add_route('GET', '/connect', ws_handler)
    app.router.add_static('/', settings.WEB_ROOT)

    app.on_shutdown.append(on_shutdown)

    web.run_app(app, host=host, port=port)


run()

