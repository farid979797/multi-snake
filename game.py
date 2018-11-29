from random import randint, choice
from collections import OrderedDict
from uuid import uuid4

import settings
from world import World
from snake import Snake
from player import Player
from messaging import json, Messaging
from datatypes import Char, Draw, Render
from exceptions import SnakeError


class Game(Messaging):
    GAME_OVER_TEXT = ">>> GAME OVER <<<"

    def __init__(self):
        self._colors = []
        self._players = OrderedDict()
        self._world = World()
        self.frame = 0
        self.running = False
        self.speed = settings.GAME_SPEED
        self.settings = {attr: getattr(settings, attr) for attr, _ in settings.SNAKEPIT_SETTINGS}

    def __repr__(self):
        return '<%s [players=%s]>' % (self.__class__.__name__, len(self._players))

    async def _send_msg(self, player, *args):
        for ws in player.wss:
            await self._send_one(ws, [args])

    async def _send_msg_all_multi(self, messages):
        if messages:
            wss = (ws for player in self._players.values() for ws in player.wss)
            await self._send_all(wss, messages)

    async def _send_msg_all(self, *args):
        await self._send_msg_all_multi([args])

    async def send_error_all(self, msg):
        await self._send_msg_all(self.MSG_ERROR, msg)

    @classmethod
    async def close_player_connection(cls, player, **kwargs):
        for ws in player.wss:
            await cls._close(ws, **kwargs)

    @staticmethod
    def _pick_random_color():
        return randint(1, settings.NUM_COLORS)

    def _pick_player_color(self):
        # выберем рандомный цвет
        if not len(self._colors):
            # нулевой цвет зарезервировван для интерфейса
            self._colors = list(range(1, settings.NUM_COLORS + 1))

        color = choice(self._colors)
        self._colors.remove(color)

        return color

    def _return_player_color(self, color):
        self._colors.append(color)

    @staticmethod
    def _render_text(text, color):
        # render in the center of play field
        pos_y = int(World.SIZE_Y / 2)
        pos_x = int(World.SIZE_X / 2 - len(text)/2)
        render = []

        for i in range(0, len(text)):
            render.append(Draw(pos_x + i, pos_y, text[i], color))

        return render

    def _apply_render(self, render):
        messages = []

        for draw in render:
            self._world[draw.y][draw.x] = Char(draw.char, draw.color)
            messages.append([self.MSG_RENDER] + list(draw))

        return messages

    async def reset_world(self):
        self.frame = 0
        self.speed = settings.GAME_SPEED
        self._world.reset()
        await self._send_msg_all(self.MSG_RESET_WORLD)

    def _get_spawn_place(self):
        for i in range(0, 2):
            x = randint(0, World.SIZE_X - 1)
            y = randint(0, World.SIZE_Y - 1)

            if self._world[y][x].char == World.CH_VOID:
                return x, y

        return None, None

    def spawn_digit(self, right_now=False):
        render = []

        if right_now or randint(1, 100) <= settings.DIGIT_SPAWN_RATE:
            x, y = self._get_spawn_place()

            if x and y:
                char = str(1)
                color = self._pick_random_color()
                render += [Draw(x, y, char, color)]

        return render

    def spawn_stone(self, right_now=False):
        render = []

        if right_now or randint(1, 100) <= settings.STONE_SPAWN_RATE:
            x, y = self._get_spawn_place()

            if x and y:
                render += [Draw(x, y, World.CH_STONE, World.COLOR_0)]

        return render

    @property
    def top_scores(self):
        return [(t[0], t[1], randint(1, settings.NUM_COLORS)) for t in self._top_scores]

    @property
    def players_alive_count(self):
        return sum(int(p.alive) for p in self._players.values())

    def get_player_by_color(self, color):
        for player in self._players.values():
            if player.color == color:
                return player

        return None

    async def new_player(self, name, ws, player_id=None):
        if player_id:
            if player_id in self._players:
                player = self._players[player_id]
                player.add_connection(ws)

                return player
        else:
            player_id = str(uuid4())

        player = Player(player_id, name, ws)

        await self._send_msg(player, self.MSG_HANDSHAKE, player.name, player.id, self.settings)
        await self._send_msg(player, self.MSG_SYNC, self.frame, self.speed)
        await self._send_msg(player, self.MSG_WORLD, self._world)
        await self._send_msg(player, self.MSG_TOP_SCORES, self.top_scores)

        for p in self._players.values():
            if p.alive:
                await self._send_msg(player, self.MSG_P_JOINED, p.id, p.name, p.color, p.score)

        self._players[player.id] = player

        return player

    async def join(self, player):
        if player.alive:
            return

        if self.players_alive_count == settings.MAX_PLAYERS:
            await self._send_msg(player, self.MSG_ERROR, "Maximum players reached")
            return

        color = self._pick_player_color()

        player.new_snake(self.settings, self._world, color)
        # уведомим всех о появлении нового игрока
        await self._send_msg_all(self.MSG_P_JOINED, player.id, player.name, player.color, player.score)

    async def game_over(self, player, ch_hit=None, frontal_crash=False, force=False):
        player.alive = False
        messages = [[self.MSG_P_GAMEOVER, player.id]]

        if frontal_crash:
            pass
        elif ch_hit and ch_hit.char in Snake.BODY_CHARS:
            killer = self.get_player_by_color(ch_hit.color)

            if killer:
                if killer == player:
                    pass
                elif killer.alive:
                    killer.score += settings.KILL_POINTS
                    messages.append([self.MSG_P_SCORE, killer.id, killer.score])

        await self._send_msg_all_multi(messages)
        self._return_player_color(player.color)
        self._calc_top_scores(player)
        self._store_top_scores()
        await self._send_msg_all(self.MSG_TOP_SCORES, self.top_scores)

        render = player.snake.render_game_over()

        if not self.players_alive_count:
            render += self._render_text(self.GAME_OVER_TEXT, self._pick_random_color())

        return render

    async def player_disconnected(self, player):
        player.shutdown()

        if player.alive:
            render = await self.game_over(player, force=True)
            messages = self._apply_render(render)
            await self._send_msg_all_multi(messages)

        self._players.pop(player.id, None)
        del player

    async def disconnect_closed(self):
        for player in list(self._players.values()):
            if player.is_connection_closed():
                await self.player_disconnected(player)

    async def kill_all(self):
        render = []

        for player in self._players.values():
            if player.alive:
                render += await self.game_over(player, force=True)

        messages = self._apply_render(render)
        await self._send_msg_all_multi(messages)

    async def shutdown(self, code=Messaging.WSCloseCode.GOING_AWAY, message='Server shutdown'):
        for player in list(self._players.values()):
            await self.close_player_connection(player, code=code, message=message)

