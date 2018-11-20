from collections import namedtuple, OrderedDict


Position = namedtuple('Position', 'x y')

Vector = namedtuple('Vector', 'xdir ydir')

Char = namedtuple('Char', 'char color')

Draw = namedtuple('Draw',  'x y char color')


class Render(OrderedDict):
    def append(self, draw):
        assert isinstance(draw, Draw)
        self[Position(draw.x, draw.y)] = draw

    def extend(self, draws):
        for draw in draws:
            self.append(draw)

    def __iadd__(self, other):
        if isinstance(other, list):
            self.extend(other)
            return self
        else:
            raise TypeError('unsupported operand type(s) for +=')
