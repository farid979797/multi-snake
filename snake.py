from collections import deque
from random import randint

import settings
from datatypes import Vector, Position, Draw
from exceptions import SnakeError, SnakePlacementError
from world import World


class BaseSnake:
    COLOR_0 = World.COLOR_0
    CH_VOID = World.CH_VOID
    CH_STONE = World.CH_STONE

    CH_HEAD = '$'
    CH_BODY = '*'
    CH_TAIL = '$'
    BODY_CHARS = frozenset([CH_HEAD, CH_BODY, CH_TAIL])

    CH_DEAD_HEAD = 'x'
    CH_DEAD_BODY = '+'
    CH_DEAD_TAIL = 'x'
    DEAD_BODY_CHARS = frozenset([CH_DEAD_HEAD, CH_DEAD_BODY, CH_DEAD_TAIL])

    UP = Vector(0, -1)
    DOWN = Vector(0, 1)
    LEFT = Vector(-1, 0)
    RIGHT = Vector(1, 0)

    DIRECTIONS = (UP, DOWN, LEFT, RIGHT)

    color = None
    alive = False

    def __init__(self, game_settings, world, color):
        self._game_settings = game_settings
        self._world = world
        self.color = color
        self.alive = True

    def __repr__(self):
        return '<%s [color=%s]>' % (self.__class__.__name__, self.color)


class Snake(BaseSnake):
    grow = 0
    body = ()
    direction = None
    current_direction = None

    def __init__(self, *args, **kwargs):
        super(Snake, self).__init__(*args, **kwargs)
        self.body = deque()
        self.grew = False

    def reset(self):
        self.grow = 0
        self.body.clear()
        self.direction = self.current_direction = None

    def create(self):
        assert not self.grow
        assert not self.body
        assert not self.direction

        # try to spawn snake at some distance from world's borders
        distance = settings.INIT_LENGTH + settings.INIT_MIN_DISTANCE_BORDER
        x = randint(distance, World.SIZE_X - distance)
        y = randint(distance, World.SIZE_Y - distance)
        self.direction = self.current_direction = self.DIRECTIONS[randint(0, 3)]
        # create snake from tail to head
        render = []
        pos = Position(x, y)

        for i in range(0, settings.INIT_LENGTH):
            target = self._world[pos.y][pos.x]

            if target.char != self.CH_VOID:
                raise SnakePlacementError('Cannot place snake on %r because the position '
                                          'is occupied by %r', pos, target)

            if i == 0:
                char = self.CH_TAIL
            elif i == settings.INIT_LENGTH - 1:
                char = self.CH_HEAD
            else:
                char = self.CH_BODY

            self.body.appendleft(pos)
            render.append(Draw(pos.x, pos.y, char, self.color))
            pos = self.next_position()

        return render

    def render_new(self):
        render = None

        for i in range(0, settings.INIT_RETRIES):
            try:
                render = self.create()
            except SnakePlacementError:
                self.reset()
            else:
                break

        if not render:
            raise SnakeError('There is no place for a new snake in this world :(')

        return render

    def next_position(self):
        # next position of the snake's head
        return Position(self.body[0].x + self.direction.xdir,
                        self.body[0].y + self.direction.ydir)

    def render_move(self, ignore_tail=False):
        # moving snake to the next position
        render = []
        new_head = self.next_position()
        self.body.appendleft(new_head)
        # draw head in the next position
        render.append(Draw(new_head.x, new_head.y, self.CH_HEAD, self.color))
        # draw body in the old place of head
        render.append(Draw(self.body[1].x, self.body[1].y, self.CH_BODY, self.color))
        # save current direction of the head
        self.current_direction = self.direction

        # if we grow this turn, the tail remains in place
        if self.grow > 0:
            self.grow -= 1
            self.grew = True
        else:
            self.grew = False
            # otherwise the tail moves
            old_tail = self.body.pop()
            if not ignore_tail:
                render.append(Draw(old_tail.x, old_tail.y, self.CH_VOID, self.COLOR_0))
            new_tail = self.body[-1]
            render.append(Draw(new_tail.x, new_tail.y, self.CH_TAIL, self.color))

        return render

    def render_game_over(self):
        render = []

        # dead snake
        for i, pos in enumerate(self.body):
            if i == 0:
                render.append(Draw(pos.x, pos.y, self.CH_DEAD_HEAD, self.COLOR_0))
            elif i == len(self.body) - 1:
                render.append(Draw(pos.x, pos.y, self.CH_DEAD_TAIL, self.COLOR_0))
            else:
                render.append(Draw(pos.x, pos.y, self.CH_DEAD_BODY, self.COLOR_0))

        return render
