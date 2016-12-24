import time
import random
from collections import OrderedDict, namedtuple, defaultdict

import dictionary
from dice import DICE_FACES
from deterministic_board import deterministic_boards


class Player(object):

    def __init__(self, color):
        self.color = color
        self.score = 0
        self.wins = 0
        self.word = Word(self)
        self.guess = Word(self)
        self.seen_positions = set()
        self.last_position = None
        self.is_guessing = False
        self.sid = None
        self.message = None

    def pop_message(self):
        if self.message:
            message = self.message
            self.message = None
            return message
        return None

    def set_message(self, text):
        self.message = Message(text, type='message')

    def set_error(self, text):
        self.message = Message(text, type='error')

    def to_visible_dict(self):
        return {
            'color': self.color,
            'score': self.score,
            'wins': self.wins,
        }

    def start_round(self):
        self.seen_positions = set()
        self.last_position = None
        self.start_turn()

    def start_turn(self):
        self.last_position = None
        self.word = Word(self)
        self.guess = Word(self)
        self.is_guessing = False

    def is_adjacent_to_last_position(self, position):
        if self.last_position is None:
            return True

        px, py = position
        lx, ly = self.last_position
        print px, py, lx, ly, 'diffs', abs(px - lx) <= 1, abs(py - ly) <= 1
        return abs(px - lx) <= 1 and abs(py - ly) <= 1

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


class Game(object):

    def __init__(self, game_id,
                 max_turn_time=20,
                 num_turns=3,
                 width=5,
                 is_deterministic=False):

        self.game_id = game_id
        self.max_turn_time = max_turn_time
        self.num_turns = num_turns
        self.width = width
        self.is_deterministic = is_deterministic
        self.board = self.roll_dice()
        self.players = OrderedDict()
        self.words = []
        self.state = State.NOT_STARTED
        self.turn = 0
        self.turn_end_time = float('infinity')
        self.turns_left = 0

    def add_player(self, color):
        player = Player(color)
        self.players[color] = player
        return player

    def player_turn(self):
        return self.players.values()[self.turn]

    def start_round(self):
        if self.is_deterministic:
            self.turn = 0
        else:
            self.turn = random.randint(0, len(self.players) - 1)

        print '>>>>>>>>>>>>>>>> start round: %d' % self.turn

        self.state = State.PLAYING
        self.turn_end_time = time.time() + self.max_turn_time
        self.turns_left = self.num_turns * len(self.players)
        self.board = self.roll_dice()
        self.words = []
        for player in self.players.values():
            player.start_round()

    def turn_time_left(self):
        return self.turn_end_time - time.time()

    def turn_out_of_time(self):
        return self.turn_time_left() <= 0

    def next_turn(self):
        self.turns_left -= 1
        if self.turns_left == 0:
            self.end_round()

        else:
            self.turn = (self.turn + 1) % len(self.players)
            self.player_turn().start_turn()
            self.turn_end_time = time.time() + self.max_turn_time

        print '>>>>>>>>>>>>>>>> next turn: %d' % self.turn

    def end_round(self):
        self.state = State.ENDED
        self.update_player_scores()

    def player_at(self, x, y):
        cell = self.board[(x, y)]

        for p in self.players.values():
            if p.word.contains(cell):
                return p

        for word in self.words:
            if word.contains(cell):
                return word.player

        return None

    def get_existing_word(self, word):
        for w in self.words:
            if w.is_equivalent(word):
                return w

        return None

    def add_word(self, word):
        self.words.append(word)

    def board_view_dict(self, player):
        res = [[{
            'letter': self.board[(x, y)].letter,
            'value': '%s|%d,%d' % (self.board[(x, y)].letter, x, y),
            'position': '%d,%d' % (x, y),
            'disabled': ((not player.is_guessing) and
                         ((x, y) in player.seen_positions)),
            'color': (self.player_at(x, y).color
                      if self.player_at(x, y)
                      and (x, y) in player.seen_positions
                      else None)}
                 for y in range(self.width)]
                for x in range(self.width)]
        return res

    def full_board_view_dict(self):
        return [[{
            'letter': self.board[(x, y)].letter,
            'value': '%s|%d,%d' % (self.board[(x, y)].letter, x, y),
            'position': '%d,%d' % (x, y),
            'disabled': True,
            'color': (self.player_at(x, y).color
                      if self.player_at(x, y)
                      else None)}
                 for y in range(self.width)]
                for x in range(self.width)]

    def words_by_player(self):
        ret = defaultdict(list)
        for word in self.words:
            ret[word.player.color].append(word)
        return ret

    def update_player_scores(self):
        words_by_player = self.words_by_player()

        player_scores = defaultdict(list)
        for p in self.players.values():
            words = words_by_player[p.color]
            score = score_words(words)
            player_scores[score].append(p)
            p.score += score

        max_score = max(player_scores)
        for p in player_scores[max_score]:
            p.wins += 1

    def gather_results(self):
        results = []
        words_by_player = self.words_by_player()
        for p in self.players.values():
            words = words_by_player[p.color]
            words = sorted(words, key=lambda w: w.score(), reverse=True)
            score = score_words(words)
            results.append(Result(color=p.color, words=words, score=score))

        return sorted(results, key=lambda r: r.score, reverse=True)

    def started(self):
        return self.state != State.NOT_STARTED

    def playing(self):
        return self.state == State.PLAYING

    def ended(self):
        return self.state == State.ENDED

    def end(self):
        self.state = State.ENDED

    def roll_dice(self):
        board = {}

        if self.is_deterministic:
            for x in range(self.width):
                for y in range(self.width):
                    letter = deterministic_boards[self.width][x][y]
                    board[(x, y)] = BoardCell(letter, (x, y))

        else:
            dices = [d for d in DICE_FACES[self.width]] # copy
            random.shuffle(dices)
            for x in range(self.width):
                for y in range(self.width):
                    i = x * self.width + y
                    letters = dices[i]
                    letter = letters[random.randint(0, len(letters) - 1)]
                    board[(x, y)] = BoardCell(letter, (x, y))

        return board


class Message(namedtuple('Message', 'text type')):
    pass


class Result(namedtuple('Result', 'color words score')):
    pass


class Word(object):

    def __init__(self, player):
        self.player = player
        self.cells = []
        self.previous_owner_colors = set()

    def letters(self):
        return ''.join([c.letter.lower() for c in self.cells])

    def score(self):
        assert dictionary.contains(self)
        return dictionary.score(self)

    def append(self, cell):
        self.cells.append(cell)

    def contains(self, cell):
        return cell in self.cells

    def is_equivalent(self, other):
        return (frozenset(self.cells) == frozenset(other.cells)
                and self.letters() == other.letters())

    def __len__(self):
        return len(self.cells)

    def steal(self, new_player):
        self.previous_owner_colors.add(self.player.color)
        self.player = new_player
        for cell in self.cells:
            new_player.seen_positions.add(cell.position)


def score_words(words):
    return sum([w.score() for w in words])


class BoardCell(namedtuple('BoardCell', 'letter position')):
    pass


class State(object):
    NOT_STARTED = 'NOT_STARTED'
    PLAYING = 'PLAYING'
    ENDED = 'ENDED'
