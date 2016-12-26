import math
import random
from collections import namedtuple

from snoggle.dictionary import COMMON_WORDS
from snoggle.word import Word
from snoggle.abstract_player import AbstractPlayer
from snoggle.board import BoardView

DIRECTIONS = [(_x, _y) for _x in range(-1, 2) for _y in range(-1, 2)
              if not (_x == 0 and _y == 0)]

class BotPlayer(AbstractPlayer):

    def __init__(self, color, vocabulary_size=20000, num_attempts=10,
                 num_candidate_words=20, num_word_attempts=1000,
                 return_word_prob=1, guessiness=0.6, vocabulary=None):
        super(BotPlayer, self).__init__(color)
        self.num_attempts = num_attempts
        self.num_candidate_words = num_candidate_words
        self.num_word_attempts = num_word_attempts
        self.return_word_prob = return_word_prob
        self.guessiness = guessiness
        self.is_bot = True
        self.vocabulary = vocabulary or make_vocabulary(vocabulary_size)
        self.prefix_vocabulary = make_prefix_set(self.vocabulary)
        self.thought_word = None
        self.all_guesses_and_words = [] # including previous words, to keep track of stolen

    def position_is_in_board(self, board, x, y):
        return (x >= 0
                and y >= 0
                and x < board.width
                and y < board.width)

    def adjacent_positions(self, board, position, previous_positions,
                          other_colors=False, other_color=None):
        x, y = position
        directions = random.sample(DIRECTIONS, 8)
        positions = []
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if not self.position_is_in_board(board, nx, ny):
                continue
            if (nx, ny) in previous_positions:
                continue

            if other_colors:
                cell_color = board.color_at(nx, ny)
                if other_color:
                    if not (cell_color is None or cell_color == other_color):
                        continue
                else:
                    if cell_color == self.color:
                        continue
            else:
                if board.color_at(nx, ny) is not None:
                    continue

            positions.append((nx, ny))

        return positions

    def initial_position(self, board, other_colors=False):
        for _ in range(100):
            x = random.randint(0, board.width - 1)
            y = random.randint(0, board.width - 1)

            if other_colors:
                if board.color_at(x, y) != self.color:
                    return x, y
            else:
                if board.color_at(x, y) is None:
                    return x, y

        return None

    def is_in_vocabulary(self, word):
        return word.letters().lower() in self.vocabulary

    def find_random_word_in_board(self, board, other_colors=False,
                                  words=frozenset()):
        initial = self.initial_position(board, other_colors=other_colors)
        if not initial:
            return None

        other_color = board.color_at(*initial)

        word = Word(self)
        position = initial

        word_letters = set([w.letters() for w in words])

        word.append(board.cell_at(*initial))

        while True:
            previous_positions = word.positions()

            for x, y in self.adjacent_positions(
                    board, position, previous_positions,
                    other_colors=other_colors, other_color=other_color):
                if (word.letters() + board.cell_at(x, y).letter.lower() in
                    self.prefix_vocabulary):
                    position = (x, y)
                    break
            else:
                return None

            x, y = position

            if other_colors:
                cell_color = board.color_at(x, y)
                if other_color:
                    if cell_color != other_color and cell_color is not None:
                        continue
                else:
                    other_color = cell_color

            word.append(board.cell_at(x, y))

            #print word.letters(), self.is_in_vocabulary(word), word.letters() in self.prefix_vocabulary

            if word.letters() not in self.prefix_vocabulary:
                return None

            if (random.random() < self.return_word_prob
                and self.is_in_vocabulary(word)
                and word.letters() not in word_letters):
                return word

        return word

    def find_random_guesses_in_board(self, board):
        words = []
        for _ in range(self.num_word_attempts):
            word = self.find_random_word_in_board(board, other_colors=True, words=words)
            if (word and self.is_in_vocabulary(word)
                and not self.has_used_guess_before(word)):
                words.append(word)

            if len(words) == self.num_candidate_words:
                return words

        return words

    def sort_guesses_by_number_of_seen_cells(self, board, words):
        def num_seen_cells(word):
            num_seen = 0
            for cell in word.cells:
                x, y = cell.position
                color = board.color_at(x, y)
                if color is not None:
                    num_seen += 1
            return num_seen
        return sorted(words, key=num_seen_cells, reverse=True)

    def make_guess(self, board):
        words = self.find_random_guesses_in_board(board)

        words = self.sort_guesses_by_number_of_seen_cells(board, words)

        for word in words:
            if random.random() < 0.9:
                self.is_guessing = True
                self.guess = word
                self.all_guesses_and_words.append(word)
                return True

        return False

    def has_used_guess_before(self, word):
        for previous in self.all_guesses_and_words:
            if word.is_equivalent(previous):
                return True
        return False

    def next_position(self):
        i = len(self.word)
        return self.thought_word.cells[i].position

    def thought_word_is_impossible(self, board):
        for i in range(len(self.word), len(self.thought_word)):
            x, y = self.thought_word.cells[i].position
            if board.color_at(x, y) is not None:
                return True
        return False

    def wants_to_guess(self):
        return random.random() < self.guessiness

    def find_random_words_in_board(self, board):
        words = []
        for _ in range(self.num_word_attempts):
            word = self.find_random_word_in_board(board, words=words)
            if word and self.is_in_vocabulary(word):
                words.append(word)

            if len(words) == self.num_candidate_words:
                return words

        return words

    def think_of_word(self, board):
        words = self.find_random_words_in_board(board)
        if not words:
            return False

        subsample = random.sample(words, min(len(words), 3))
        longest_of_subsample = sorted(subsample, key=len, reverse=True)[0]

        self.thought_word = longest_of_subsample
        return True

    def take_action(self, board):
        if (self.thought_word is None
            or self.thought_word_is_impossible(board)):

            if self.wants_to_guess():
                success = self.make_guess(board)
                if success:
                    print 'bot guess: ', self.guess.letters()
                    return BotSubmitAction()
                else:
                    return None

            else:
                self.is_guessing = False
                self.word = Word(self)
                success = self.think_of_word(board)
                if not success:
                    print 'bot failed to think of word'
                    return None
                print 'bot trying word: ', self.thought_word.letters()

        if self.word.is_equivalent(self.thought_word):
            print 'bot submitting word: ', self.word.letters()
            return BotSubmitAction()

        x, y = self.next_position()

        return BotSelectAction(x, y)

    def submit_successful(self):
        if self.is_guessing:
            self.all_guesses_and_words.append(self.guess)
        else:
            self.all_guesses_and_words.append(self.word)
        self.thought_word = None

    def action_failed(self):
        if self.is_guessing:
            self.clear_guess()
        else:
            self.clear_word()
        self.thought_word = None

    def learn_word(self, w):
        self.vocabulary.add(w)
        for i in range(1, 1 + len(w)):
            self.prefix_vocabulary.add(w[:i])


class BotSelectAction(namedtuple('BotSelectAction', 'x y')):
    pass

class BotSubmitAction(object):
    pass


def make_vocabulary(size):
    words = COMMON_WORDS
    prob = 1.0
    ret = set()
    prob_change = 0.45 ** (1. / (min(len(words), size * 2) / 2))
    for w in words:
        if random.random() <= prob:
            ret.add(w)
        if len(ret) == size:
            break
        prob *= prob_change
    return ret


def make_prefix_set(vocabulary):
    prefixes = set()
    for w in vocabulary:
        for i in range(1, 1 + len(w)):
            prefixes.add(w[:i])

    return prefixes
