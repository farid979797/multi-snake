from exceptions import ImproperlyConfigured, ValidationError
from game import Game


def get_client_address(request):
    peername = request.transport.get_extra_info('peername')

    if isinstance(peername, (list, tuple)):
        return peername[0]
    else:
        return peername


def validate_settings(settings):
    if settings.MAX_PLAYERS > settings.NUM_COLORS:
        raise ImproperlyConfigured('Invalid MAX_PLAYERS (> NUM_COLORS)')

    if settings.FIELD_SIZE_X < len(Game.GAME_OVER_TEXT):
        raise ImproperlyConfigured('Invalid FIELD_SIZE_X (< %d)' % len(Game.GAME_OVER_TEXT))

    distance = settings.INIT_LENGTH + settings.INIT_MIN_DISTANCE_BORDER

    if settings.FIELD_SIZE_X / 2 < distance:
        raise ImproperlyConfigured('Invalid FIELD_SIZE_X, INIT_LENGTH or INIT_MIN_DISTANCE_BORDER')

    if settings.FIELD_SIZE_Y / 2 < distance:
        raise ImproperlyConfigured('Invalid FIELD_SIZE_Y, INIT_LENGTH or INIT_MIN_DISTANCE_BORDER')


def validate_string(value, min_length=None, max_length=None):
    try:
        value = str(value)
    except ValueError:
        raise ValidationError('Not a string.')

    if ((min_length is not None and len(value) < min_length) or
            (max_length is not None and len(value) > max_length)):
        raise ValidationError('Invalid value.')

    return value


def validate_player_name(value):
    try:
        return validate_string(str(value).strip(), min_length=1, max_length=15)
    except ValueError:
        raise ValidationError('Invalid player name.')


def validate_player_id(value):
    try:
        return validate_string(value, min_length=1, max_length=36)
    except ValueError:
        raise ValidationError('Invalid player ID.')
