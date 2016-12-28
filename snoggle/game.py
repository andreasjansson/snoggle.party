# -*- coding: utf-8 -*-

import time
import random
from collections import OrderedDict, namedtuple, defaultdict

from snoggle.dice import DICE_FACES
from snoggle.deterministic_board import deterministic_boards
from snoggle.human_player import HumanPlayer
from snoggle.bot_player import BotPlayer
from snoggle.word import score_words
from snoggle.board import BoardView, make_board_view_cell, BoardCell


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
        self.turn_start_time = 0
        self.turn_end_time = float('infinity')
        self.turns_left = 0

    def add_human_player(self, color):
        player = HumanPlayer(color)
        self.players[color] = player
        return player

    def human_players(self):
        return [p for p in self.players.values()
                if not p.is_bot]

    def player_turn(self):
        return self.players.values()[self.turn]

    def start_round(self):
        if self.is_deterministic:
            self.turn = 0
        else:
            self.turn = random.randint(0, len(self.players) - 1)

        print '>>>>>>>>>>>>>>>> start round: %d' % self.turn

        self.state = State.PLAYING

        self.turn_start_time = time.time()
        self.turn_end_time = self.get_turn_end_time()
        self.turns_left = self.num_turns * len(self.players)
        self.board = self.roll_dice()
        self.words = []
        for player in self.players.values():
            player.start_round()

    def get_turn_end_time(self):
        if self.player_turn().is_bot:
            if self.is_deterministic:
                turn_time = 1
            else:
                turn_time = random.randint(2, self.max_turn_time)
        else:
            turn_time = self.max_turn_time

        return time.time() + turn_time

    def turn_time_left(self):
        return self.turn_end_time - time.time()

    def turn_time_left_display(self):
        return self.turn_start_time + self.max_turn_time - time.time()

    def turn_out_of_time(self):
        return self.turn_time_left() <= 0

    def next_turn(self):
        self.turns_left -= 1
        if self.turns_left == 0:
            self.end_round()

        else:
            self.turn = (self.turn + 1) % len(self.players)
            self.player_turn().start_turn()
            self.turn_start_time = time.time()
            self.turn_end_time = self.get_turn_end_time()

        print '>>>>>>>>>>>>>>>> next turn: %d' % self.turn

    def end_round(self):
        self.state = State.ENDED
        self.update_player_scores()
        self.teach_robots_new_words()

    def teach_robots_new_words(self):
        all_words = set()
        for w in self.words:
            all_words.add(w.letters())
        for p in self.players.values():
            if p.is_bot:
                for w in all_words:
                    if w not in p.vocabulary:
                        p.learn_word(w)
                        print 'bot learned new word', w

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

    def board_view(self, player):
        return BoardView([
            make_board_view_cell(
                letter=self.board[(x, y)].letter,
                x=x,
                y=y,
                disabled=((not player.is_guessing) and
                          ((x, y) in player.seen_positions)),
                color=(self.player_at(x, y).color
                   if self.player_at(x, y)
                       and (x, y) in player.seen_positions
                   else None))
            for x in range(self.width)
            for y in range(self.width)
        ])

    def full_board_view(self):
        return BoardView([
            make_board_view_cell(
                letter=self.board[(x, y)].letter,
                x=x,
                y=y,
                disabled=True,
                color=(self.player_at(x, y).color
                       if self.player_at(x, y)
                       else None))
            for x in range(self.width)
            for y in range(self.width)
        ])

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
                    letter = deterministic_boards[self.width][y][x]
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

    def check_word_and_guess(self, player, end_of_turn=False):
        word = player.guess if player.is_guessing else player.word

        if len(word) == 0:
            return False

        letters = word.letters().upper()

        if player.is_guessing:
            existing_word = self.get_existing_word(word)

            if existing_word:
                if player.color in existing_word.previous_owner_colors:
                    player.set_error('You owned that before!')
                    player.clear_guess()

                else:
                    previous_owner = existing_word.player
                    existing_word.steal(player)
                    player.set_steal_message('You stole %s!' % letters)
                    previous_owner.set_steal_message('%s stole %s!' % (
                        player.color.capitalize(), letters))

                    if not end_of_turn:
                        self.next_turn()
                    return True

            else:
                if not end_of_turn:
                    player.set_error(u'Nope 😞')
                    player.clear_guess()

        else:
            if word.is_in_dictionary():
                self.add_word(word)
                player.set_success_message(
                    '%s: %d points!' % (letters, word.score()))
                if not end_of_turn:
                    self.next_turn()
                return True

            else:
                player.clear_word()
                if not end_of_turn:
                    player.set_error('%s is not a word' % letters)

        return False

    def player_select_cell(self, player, x, y):
        cell = self.board[(x, y)]

        if player.is_guessing:
            player.guess.append(cell)
            return True

        else:
            if (x, y) in player.seen_positions:
                return False

            if not player.is_adjacent_to_last_position((x, y)):
                return False

            player.seen_positions.add((x, y))

            if not self.player_at(x, y):
                player.last_position = (x, y)
                player.word.append(cell)
                return True

            return False

    def add_bot(self, color):
        self.players[color] = BotPlayer(color)

    def delete_bot(self, color):
        del self.players[color]


Result = namedtuple('Result', 'color words score')


class State(object):
    NOT_STARTED = 'NOT_STARTED'
    PLAYING = 'PLAYING'
    ENDED = 'ENDED'
