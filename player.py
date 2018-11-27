from messaging import Messaging
from snake import Snake


class Player:
    snake = None

    def __init__(self, player_id, name, ws):
        self.id = player_id
        self.name = name
        self.wss = []
        self.score = 0
        self.keymap = {
            Messaging.CMD_LEFT: Snake.LEFT,
            Messaging.CMD_UP: Snake.UP,
            Messaging.CMD_RIGHT: Snake.RIGHT,
            Messaging.CMD_DOWN: Snake.DOWN,
        }
        self.add_connection(ws)

    def __repr__(self):
        return '<%s [id=%s] [name=%s] [color=%s]>' % (self.__class__.__name__, str(self.id)[:8], self.name, self.color)

    def add_connection(self, ws):
        self.wss.append(ws)

    def shutdown(self):
        self.wss.clear()

    def is_connection_closed(self):
        return any(ws.closed or ws.close_code for ws in self.wss)

    def new_snake(self, game_settings, world, color):
        self.snake = Snake(game_settings, world, color)

    def keypress(self, code):
        if not self.alive:
            return

        direction = self.keymap.get(code)
        snake_direction = self.snake.direction

        if direction and snake_direction:
            # do not move in the opposite direction
            if snake_direction == self.snake.current_direction and not (
                    direction.xdir == -snake_direction.xdir and
                    direction.ydir == -snake_direction.ydir):
                self.snake.direction = direction

    @property
    def alive(self):
        if self.snake:
            return self.snake.alive
        else:
            return False

    @alive.setter
    def alive(self, value):
        self.snake.alive = value

    @property
    def color(self):
        if self.snake:
            return self.snake.color
        else:
            return None

    @property
    def direction(self):
        if self.snake:
            return self.snake.direction
        else:
            return None
