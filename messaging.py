import json
from aiohttp import WSCloseCode


class Messaging:
    """
    WebSocket messaging helper class.
    """
    WSCloseCode = WSCloseCode

    MSG_JOIN = 'join'
    MSG_NEW_PLAYER = 'new_player'
    MSG_HANDSHAKE = 'handshake'
    MSG_WORLD = 'world'
    MSG_P_JOINED = 'p_joined'
    MSG_P_GAMEOVER = 'p_gameover'
    MSG_P_SCORE = 'p_score'
    MSG_RESET_WORLD = 'reset_world'
    MSG_TOP_SCORES = 'top_scores'
    MSG_RENDER = 'render'
    MSG_ERROR = 'error'
    MSG_PING = 'ping'
    MSG_PONG = 'pong'
    MSG_SYNC = 'sync'

    CMD_LEFT = 37
    CMD_UP = 38
    CMD_RIGHT = 39
    CMD_DOWN = 40

    @staticmethod
    async def _send_one(ws, message):
        msg = json.dumps(message)
        await ws.send_str(msg)

    @staticmethod
    async def _send_all(wss, messages):
        msg = json.dumps(messages)

        for ws in wss:
            if not ws.closed:
                await ws.send_str(msg)

    @staticmethod
    async def _close(ws, code=WSCloseCode.GOING_AWAY, message='Closing connection'):
        await ws.close(code=code, message=message)
