import os

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
WEB_ROOT = os.path.join(PROJECT_DIR, 'html')
LEADERBOARD_PATH = os.path.join(WEB_ROOT, 'leaderboard.html')

SERVER_HOST = os.environ.get('SNAKEPIT_HOST', None)
SERVER_PORT = int(os.environ.get('SNAKEPIT_PORT', 8111))
LEADERBOARD_PORT = SERVER_PORT + 1

TOP_SCORES_FILE_DEFAULT = os.path.join(PROJECT_DIR, 'scores', 'top_scores.txt')
TOP_SCORES_FILE = os.environ.get('SNAKEPIT_TOP_SCORES_FILE', TOP_SCORES_FILE_DEFAULT)


SNAKEPIT_SETTINGS = (
    ('SERVER_NAME', str),
    ('GAME_SPEED', float),
    ('GAME_SPEED_INCREASE', int),
    ('GAME_SPEED_INCREASE_RATE', float),
    ('GAME_SPEED_MAX', float),
    ('GAME_FRAMES_MAX', int),
    ('GAME_START_WAIT_FOR_PLAYERS', int),
    ('GAME_SHUTDOWN_ON_FRAMES_MAX', bool),
    ('MAX_PLAYERS', int),
    ('FIELD_SIZE_X', int),
    ('FIELD_SIZE_Y', int),
    ('KILL_POINTS', int),
    ('INIT_LENGTH', int),
    ('DIGIT_MIN', int),
    ('DIGIT_MAX', int),
    ('STONES_ENABLED', bool),
)


SERVER_NAME = 'SnakeServer'

GAME_SPEED = 4.0  # чем больше тем быстрее
GAME_SPEED_INCREASE = None  # число кадров после которого игра должна стать быстрее
GAME_SPEED_INCREASE_RATE = 0.001  # применяется к текущей скорости игры для каждого кадра
GAME_SPEED_MAX = None
GAME_FRAMES_MAX = None  # максимальное число кадров, после которого игра останавливается

GAME_START_WAIT_FOR_PLAYERS = None
GAME_SHUTDOWN_ON_FRAMES_MAX = False

MAX_PLAYERS = 6
MAX_TOP_SCORES = 15
NUM_COLORS = 6

FIELD_SIZE_X = 40
FIELD_SIZE_Y = 40

INIT_LENGTH = 5
INIT_MIN_DISTANCE_BORDER = 2
INIT_RETRIES = 10  # число попыток для рендеринга земейки

DIGIT_MIN = 1
DIGIT_MAX = 9

KILL_POINTS = 1000

STONES_ENABLED = False

DIGIT_SPAWN_RATE = 6
STONE_SPAWN_RATE = 6


# переменные окружения для игры
for setting, type_ in SNAKEPIT_SETTINGS:
    env_var = 'SNAKEPIT_' + setting

    if env_var in os.environ:
        globals()[setting] = type_(os.environ[env_var])
