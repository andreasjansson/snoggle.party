from collections import namedtuple

from snoggle.word import Word

class AbstractPlayer(object):

    def __init__(self, color):
        self.color = color
        self.score = 0
        self.wins = 0
        self.word = Word(self)
        self.guess = Word(self)
        self.seen_positions = set()
        self.is_guessing = False
        self.last_position = None
        self.is_bot = False
        self.message = None

    def start_round(self):
        self.seen_positions = set()
        self.start_turn()

    def start_turn(self):
        self.last_position = None
        self.word = Word(self)
        self.guess = Word(self)
        self.is_guessing = False

    def clear_guess(self):
        self.is_guessing = False
        self.guess = Word(self)

    def clear_word(self):
        self.last_position = None
        for cell in self.word.cells:
            self.seen_positions.remove(cell.position)
        self.word = Word(self)

    def start_guessing(self):
        self.is_guessing = True
        self.clear_word()
        self.guess = Word(self)

    def is_adjacent_to_last_position(self, position):
        if self.last_position is None:
            return True

        px, py = position
        lx, ly = self.last_position
        return abs(px - lx) <= 1 and abs(py - ly) <= 1

    def to_visible_dict(self):
        return {
            'color': self.color,
            'score': self.score,
            'wins': self.wins,
            'is_bot': self.is_bot,
        }

    def pop_message(self):
        if self.message:
            message = self.message
            self.message = None
            return message
        return None

    def set_success_message(self, text):
        self.message = Message(text, type='success-message')

    def set_steal_message(self, text):
        self.message = Message(text, type='steal-message')

    def set_error(self, text):
        self.message = Message(text, type='error')


class Message(namedtuple('Message', 'text type')):
    pass
