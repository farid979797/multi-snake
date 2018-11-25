class ImproperlyConfigured(Exception):
    pass


class SnakeError(Exception):
    pass


class SnakePlacementError(SnakeError):
    pass


class ValidationError(ValueError):
    pass
