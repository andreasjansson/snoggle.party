import time
import random
from collections import OrderedDict, namedtuple, defaultdict

import dictionary
from dice import DICE_FACES


class Player(object):

    def __init__(self, color):
        self.color = color
        self.score = 0
        self.wins = 0
        self.word = Word()
        self.guess = Word()
        self.words = set()
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
        self.words = set()
        self.start_turn()

    def start_turn(self):
        self.last_position = None
        self.word = Word()
        self.guess = Word()
        self.is_guessing = False

    def is_adjacent_to_last_position(self, position):
        if self.last_position is None:
            return True

        px, py = position
        lx, ly = self.last_position
        print px, py, lx, ly, 'diffs', abs(px - lx) <= 1, abs(py - ly) <= 1
        return abs(px - lx) <= 1 and abs(py - ly) <= 1

    def steal_word(self, other, word):
        self.words.add(word)
        other.words.remove(word)
        word.previous_owners.add(other.color)
        for cell in word.cells:
            self.seen_positions.add(cell.position)

    def clear_guess(self):
        self.is_guessing = False
        self.guess = Word()

    def clear_word(self):
        self.last_position = None
        for cell in self.word.cells:
            self.seen_positions.remove(cell.position)
        self.word = Word()

    def start_guessing(self):
        self.is_guessing = True
        self.clear_word()
        self.guess = Word()

    def add_word(self, word):
        self.words.add(word)

    def words_score(self):
        return sum([w.score() for w in self.words])


class Game(object):

    def __init__(self, game_id,
                 max_turn_time=20,
                 num_turns=3,
                 width=5):

        self.game_id = game_id
        self.max_turn_time = max_turn_time
        self.num_turns = num_turns
        self.width = width
        self.board = self.roll_dice()
        self.players = OrderedDict()
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
        self.turn = random.randint(0, len(self.players) - 1)
        self.state = State.PLAYING
        self.turn_end_time = time.time() + self.max_turn_time
        self.turns_left = self.num_turns * len(self.players)
        self.board = self.roll_dice()
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

    def end_round(self):
        self.state = State.ENDED
        self.update_player_scores()

    def update_player_scores(self):
        player_scores = defaultdict(list)
        for player in self.players.values():
            score = player.words_score()
            player_scores[score].append(player)
            player.score += score

        max_score = max(player_scores)
        for player in player_scores[max_score]:
            player.wins += 1

    def player_at(self, x, y):
        cell = self.board[(x, y)]
        for p in self.players.values():
            if cell in p.word:
                return p
            for w in p.words:
                if cell in w:
                    return p
        return None

    def player_with_word(self, word):
        for p in self.players.values():
            if word in p.words:
                return p
        return None

    def board_view_dict(self, player):
        res = [[{
            'letter': self.board[(x, y)].letter,
            'value': '%s|%d,%d' % (self.board[(x, y)].letter, x, y),
            'disabled': (x, y) in player.seen_positions,
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
            'disabled': True,
            'color': (self.player_at(x, y).color
                      if self.player_at(x, y)
                      else None)}
                 for y in range(self.width)]
                for x in range(self.width)]

    def gather_results(self):
        results = []
        for p in self.players.values():
            words = sorted(p.words, key=lambda w: w.score(), reverse=True)
            score = p.words_score()
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
        dices = [d for d in DICE_FACES[self.width]] # copy
        random.shuffle(dices)
        board = {}
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

    def __init__(self, cells=None, previous_owners=None):
        self.cells = cells or []
        self.previous_owners = previous_owners or set()

    def letters(self):
        return ''.join([c.letter.lower() for c in self.cells])

    def score(self):
        assert dictionary.contains(self)
        return dictionary.score(self)

    def append(self, cell):
        self.cells.append(cell)

    def __contains__(self, cell):
        return cell in self.cells

    def __hash__(self):
        return hash(tuple(self.cells))

    def __eq__(self, other):
        return self.cells == other.cells

    def __len__(self):
        return len(self.cells)


class BoardCell(namedtuple('BoardCell', 'letter position')):
    pass


class State(object):
    NOT_STARTED = 'NOT_STARTED'
    PLAYING = 'PLAYING'
    ENDED = 'ENDED'
