from random import choice
from copy import copy


class Tetromino:
    shape = {
        'I': (("xxxx",), ("x",) * 4),
        'J': (("xoo",
               "xxx"), ("xx",
                        "xo",
                        "xo"), ("xxx",
                                "oox"), ("ox",
                                         "ox",
                                         "xx")),
        'O': (("xx",
               "xx"),),
        'L': (("oox",
               "xxx"), ("xo",
                        "xo",
                        "xx"), ("xxx",
                                "xoo"), ("xx",
                                         "ox",
                                         "ox")),
        'S': (("oxx",
               "xxo"), ("xo",
                        "xx",
                        "ox")),
        'Z': (("xxo",
               "oxx"), ("ox",
                        "xx",
                        "xo")),
        'T': (("xxx",
               "oxo"), ("ox",
                        "xx",
                        "ox"), ("oxo",
                                "xxx"), ("xo",
                                         "xx",
                                         "xo")),
    }

    lowest_position = {
        'I': ((1, 1, 1, 1), (4,)),
        'J': ((2, 2, 2), (3, 1), (1, 1, 2), (3, 3)),
        'O': ((2, 2),),
        'L': ((2, 2, 2), (3, 3), (2, 1, 1), (1, 3)),
        'S': ((2, 2, 1), (2, 3)),
        'Z': ((1, 2, 2), (3, 2)),
        'T': ((1, 2, 1), (2, 3), (2, 2, 2), (3, 2)),
    }

    def __init__(self, shape: chr = None):
        if shape and shape not in Tetromino.shape:
            raise TypeError("wrong shape")

        self.shape = shape or Tetromino._random()
        self.rotation = 0

    def next_rotation(self):
        """rotate clockwise"""
        self.rotation += 1
        self.rotation %= len(Tetromino.shape[self.shape])
        return self

    def gen_rotation(self):
        """generate all possible rotations of tetromino"""
        duplicated = copy(self)
        yield duplicated
        duplicated.next_rotation()

        while duplicated.rotation != self.rotation:
            yield duplicated
            duplicated.next_rotation()

    def get_shape(self):
        """return tuple of strings which are tetromino representation"""
        return Tetromino.shape[self.shape][self.rotation]

    def get_highest_positions(self):
        """return tuple of ints which are highest block of tetromino"""
        return Tetromino.lowest_position[self.shape][self.rotation]

    def __str__(self):
        ret = ''
        for line in Tetromino.shape[self.shape][self.rotation]:
            ret += line + '\n'
        return ret

    def __eq__(self, other):
        if not isinstance(other, Tetromino):
            raise TypeError
        return self.shape == other.shape and self.rotation == other.rotation

    @staticmethod
    def _random():
        return choice(list(Tetromino.shape.keys()))
