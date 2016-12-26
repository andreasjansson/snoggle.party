import math
from collections import namedtuple


BoardCell = namedtuple('BoardCell', 'letter position')


BoardViewCell = namedtuple(
    'BoardCellView', 'letter value position data_position disabled color')


class BoardView(object):

    def __init__(self, cells):
        self.width = int(math.sqrt(len(cells)))
        self.cells = {c.position: c for c in cells}

    def __iter__(self):
        for y in range(self.width):
            yield [self.cells[(x, y)] for x in range(self.width)]

    def color_at(self, x, y):
        return self.cells[(x, y)].color

    def cell_at(self, x, y):
        return self.cells[(x, y)]

    def print_debug(self):
        color_map = {
            'red': 'red',
            'green': 'green',
            'purple': 'blue',
            'orange': 'grey',
            'yellow': 'yellow',
            'teal': 'cyan',
            None: None,
        }

        from termcolor import colored
        for y in range(self.width):
            for x in range(self.width):
                print colored('%2s ' % self.cell_at(x, y).letter, color_map[self.color_at(x, y)]),
            print


def make_board_view_cell(letter, x, y, disabled, color):
    return BoardViewCell(
        letter=letter,
        value='%s|%d,%d' % (letter, x, y),
        position=(x, y),
        data_position='%d,%d' % (x, y),
        disabled=disabled,
        color=color,
    )
