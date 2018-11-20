import settings
from datatypes import Char


class World(list):
    SIZE_X = settings.FIELD_SIZE_X
    SIZE_Y = settings.FIELD_SIZE_Y
    COLOR_0 = 0
    CH_VOID = ' '
    CH_STONE = '#'
    VOID_CHAR = Char(CH_VOID, COLOR_0)

    def __init__(self):
        super(World, self).__init__()
        for y in range(0, self.SIZE_Y):
            self.append([self.VOID_CHAR] * self.SIZE_X)

    def __repr__(self):
        return '<%s [%sx%s]>' % (self.__class__.__name__, self.SIZE_X, self.SIZE_Y)

    def __str__(self):
        return self.show()

    def show(self):
        border = '+' + '-' * len(self[0]) + '+'
        return border + '\n' + '\n'.join('|' + (''.join(j[0] for j in i)) + '|' for i in self) + '\n' + border

    def reset(self):
        for y in range(0, self.SIZE_Y):
            for x in range(0, self.SIZE_X):
                if self[y][x][0] != self.CH_VOID:
                    self[y][x] = self.VOID_CHAR

    def load(self, data):
        self[:] = data

    def update(self, draw):
        self[draw.y][draw.x] = Char(draw.char, draw.color)

    @classmethod
    def is_invalid_position(cls, pos):
        return pos.x < 0 or pos.x >= cls.SIZE_X or pos.y < 0 or pos.y >= cls.SIZE_Y
