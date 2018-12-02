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
        self._top_scores = self._read_top_scores()
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
    def _read_top_scores():
        try:
            with open(settings.TOP_SCORES_FILE, 'r+') as fp:
                content = fp.read()

                if content:
                    top_scores = json.loads(content)
                else:
                    top_scores = []
        except FileNotFoundError:
            top_scores = []

        return top_scores

    def _store_top_scores(self):
        with open(settings.TOP_SCORES_FILE, 'w') as fp:
            fp.write(json.dumps(self._top_scores))
            fp.close()

    def _calc_top_scores(self, player):
        if not player.score:
            return

        ts_dict = dict(self._top_scores)

        if player.score <= ts_dict.get(player.name, 0):
            return

        ts_dict[player.name] = player.score
        self._top_scores = sorted(ts_dict.items(), key=lambda x: -x[1])[:settings.MAX_TOP_SCORES]

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

    async def next_frame(self):
        self.frame += 1
        # This list may change during iteration to change the order of figuring a player's move
        # Sometimes a player's move depends on other player.
        players = list(self._players.values())
        messages = [[self.MSG_SYNC, self.frame, self.speed]]
        render_all = Render()
        new_players = []
        frontal_crashers = set()
        moves = {}

        for player in players:
            if not player.alive:
                continue

            # remember that a player was processed in this frame
            first_player_loop = player.id not in moves

            if first_player_loop:
                moves[player.id] = 0

            # check if snake already exists
            if player.snake and len(player.snake.body):
                # check next position's content
                next_pos = player.snake.next_position()

                # check bounds
                if self._world.is_invalid_position(next_pos):
                    render_all += await self.game_over(player)
                    continue

                cur_ch = self._world[next_pos.y][next_pos.x]
                next_ch = render_all.get(next_pos, None)
                grow = 0
                snake_crash = False  # hitting other living snake
                dead_crash = False  # hitting other dead snake
                tail_chase = False  # targeting a new void char
                tail_crash = False  # hitting a tail for sure
                own_tail_chaser = False

                # special cases
                if next_ch:  # check char already rendered in this frame
                    if next_ch.char in Snake.DEAD_BODY_CHARS:
                        dead_crash = True
                        logger.debug('=> %r is going to hit a dying snake', player)
                    elif next_ch.char == Snake.CH_HEAD and (cur_ch.char == World.CH_VOID or cur_ch.char.isdigit()):
                        other_player = self.get_player_by_color(next_ch.color)
                        assert other_player
                        frontal_crashers.add(player)
                        frontal_crashers.add(other_player)
                    elif next_ch.char == Snake.CH_TAIL and cur_ch.char == Snake.CH_TAIL:
                        tail_crash = True
                    elif next_ch.char == World.CH_VOID and cur_ch.char == Snake.CH_TAIL:
                        tail_chase = True
                    elif next_ch.char in Snake.BODY_CHARS:
                        snake_crash = True

                # next move
                if cur_ch.char.isdigit():  # yummy
                    # start growing next turn in case we eaten a digit
                    grow = int(cur_ch.char)
                    player.score += grow
                    messages.append([self.MSG_P_SCORE, player.id, player.score])

                elif cur_ch.char == Snake.CH_TAIL and not tail_crash and not dead_crash:  # hitting someone's tail
                    if cur_ch.color == player.color:
                        other_player = player
                        own_tail_chaser = True
                        other_player_moved = False
                    else:
                        other_player = self.get_player_by_color(cur_ch.color)
                        assert other_player
                        other_player_moved = bool(moves.get(other_player.id, False))

                    if ((not other_player_moved and other_player.snake.grow) or
                            (other_player_moved and other_player.snake.grew)):
                        # the tail won't move -> going to die anyway
                        render_all += await self.game_over(player, ch_hit=cur_ch)
                        continue
                    elif own_tail_chaser:  # make move (follow tail) + skip old tail rendering
                        pass
                    elif not tail_chase:  # wait if the other snake's tail moves
                        assert first_player_loop, 'infinite loop'
                        players.append(player)
                        continue

                elif cur_ch.char != World.CH_VOID and not tail_chase:
                    if cur_ch.char in Snake.BODY_CHARS and cur_ch.color != player.color:
                        # now the snake is going to hit another snake -> the situation depends on other snake's move
                        other_player = self.get_player_by_color(cur_ch.color)
                        assert other_player

                        if other_player.id not in moves:  # wait for the other snake's move
                            assert first_player_loop, 'infinite loop'
                            players.append(player)
                            continue

                        if other_player.alive and cur_ch.char == Snake.CH_HEAD and not snake_crash:
                            frontal_crashers.add(player)
                            frontal_crashers.add(other_player)
                            continue

                    render_all += await self.game_over(player, ch_hit=cur_ch)
                    continue

                render_all += player.snake.render_move(ignore_tail=own_tail_chaser)
                player.snake.grow += grow
                moves[player.id] += 1

            else:
                new_players.append(player)

        # render game over for players that bumped into each other with their heads
        for player in frontal_crashers:
            render_all += await self.game_over(player, frontal_crash=True)

        # render current snake moves -> update world before creating new digits and players
        messages += self._apply_render(render_all.values())
        render_all.clear()

        # spawn digits proportionally to the number of snakes alive
        for _ in range(self.players_alive_count):
            render_all += self.spawn_digit()

        # new snakes are rendered last
        for new_player in new_players:
            try:
                # newborn snake
                render_all += new_player.snake.render_new()
            except SnakeError as exc:
                await self._send_msg(new_player, self.MSG_ERROR, str(exc))
                render_all += await self.game_over(new_player)
            else:
                # and it's birthday present
                render_all += self.spawn_digit(right_now=True)  # FIXME: can be spawned over a new player

        # render new digits and snakes -> update world before creating stones
        messages += self._apply_render(render_all.values())

        # render stone
        if settings.STONES_ENABLED:
            messages += self._apply_render(self.spawn_stone())

        # send all messages
        await self._send_msg_all_multi(messages)
