from unittest2 import TestCase

from snoggle.dictionary import COMMON_WORDS
from snoggle.bot_player import BotPlayer, make_vocabulary, BotSubmitAction
from snoggle.deterministic_board import deterministic_boards
from snoggle.board import BoardView, make_board_view_cell
from snoggle.word import Word


class BotTests(TestCase):

    def setUp(self):

        board = [
            [('P', None),  ('C', None), ('A', None),      ('L', None)],
            [('U', None),  ('E', None), ('R', 'green'),   ('O', None)],
            [('E', 'red'), ('N', None), ('T', 'green'),   ('O', 'teal')],
            [('M', 'red'), ('N', None), ('T', 'teal'),    ('U', None)],
        ]

        self.board = BoardView([
            make_board_view_cell(
                letter=c[0],
                x=x,
                y=y,
                disabled=False,
                color=c[1])
            for y, row in enumerate(board)
            for x, c in enumerate(row)
        ])

        self.bot = BotPlayer(
            'red',
        #    vocabulary=set(['tool', 'art', 'pearl', 'pear'])
        )

    def test_make_vocabulary(self):
        vocabulary = make_vocabulary(100)
        self.assertEquals(len(vocabulary), 100)

        max_index = max([COMMON_WORDS.index(w) for w in vocabulary])
        self.assertGreater(max_index, 100)
        self.assertLess(max_index, 500)

    def test_adjacent_position_corner(self):
        expected_positions = set([(0, 1), (1, 0), (1, 1)])
        positions = self.bot.adjacent_positions(self.board, (0, 0), [])
        self.assertEquals(set(positions), expected_positions)

    def test_adjacent_position_none(self):
        positions = self.bot.adjacent_positions(self.board, (3, 3), [])
        self.assertEquals(positions, [])

    def test_adjacent_position_other_color(self):
        expected_positions = set([(1, 2), (2, 2), (2, 3)])
        positions = self.bot.adjacent_positions(
            self.board, (1, 3), [], other_colors=True)

        self.assertEquals(set(positions), expected_positions)

    def test_adjacent_position_specific_other_color(self):
        expected_positions = set([(1, 2), (2, 3)])
        positions = self.bot.adjacent_positions(
            self.board, (1, 3), [], other_colors=True, other_color='teal')

        self.assertEquals(set(positions), expected_positions)

    def test_adjacent_position_previous_positions(self):
        expected_positions = set([(1, 0), (1, 1), (1, 2)])
        positions = self.bot.adjacent_positions(
            self.board, (0, 1), [(0, 0)])

        self.assertEquals(set(positions), expected_positions)

    def test_adjacent_position_previous_positions_specific_color(self):
        previous_positions = [(2, 3), (3, 2), (3, 1)]

        expected_positions = set([(3, 0), (2, 0)])
        positions = self.bot.adjacent_positions(
            self.board, (3, 1), previous_positions)

        self.assertTrue(set(positions), expected_positions)

    def test_find_random_guesses_in_board(self):
        guesses = self.bot.find_random_guesses_in_board(self.board)
        self.assertEquals(len(guesses), self.bot.num_candidate_words)
        for w in guesses:
            colors = set([c.color for c in w.cells if c.color is not None])
            self.assertFalse(colors & set(['red']))
            self.assertLessEqual(len(colors), 1)

    def test_find_random_words_in_board(self):
        words = self.bot.find_random_words_in_board(self.board)
        for w in words:
            colors = [c.color for c in w.cells if c.color]
            self.assertTrue(all([c is None for c in colors]))

    def test_think_of_word(self):
        for _ in range(10):
            self.assertTrue(self.bot.think_of_word(self.board))
            for cell in self.bot.thought_word.cells:
                self.assertEquals(cell.color, None)

    def test_thought_word_is_impossible(self):
        self.bot.thought_word = Word(self.bot)
        positions = [(0, 0), (1, 1), (2, 0)]
        for x, y in positions:
            self.bot.thought_word.append(self.board.cell_at(x, y))

        self.assertFalse(self.bot.thought_word_is_impossible(self.board))

        self.board.cells[(2, 0)] = self.board.cell_at(2, 0)._replace(color='red')
        self.assertTrue(self.bot.thought_word_is_impossible(self.board))

        self.board.cells[(2, 0)] = self.board.cell_at(2, 0)._replace(color='teal')
        self.assertTrue(self.bot.thought_word_is_impossible(self.board))

        self.board.cells[(0, 0)] = self.board.cell_at(0, 0)._replace(color='red')
        self.board.cells[(2, 0)] = self.board.cell_at(2, 0)._replace(color=None)
        self.bot.word = Word(self.bot)
        self.bot.word.append(self.board.cell_at(0, 0))
        self.assertFalse(self.bot.thought_word_is_impossible(self.board))

        self.board.cells[(1, 1)] = self.board.cell_at(2, 0)._replace(color='red')
        self.assertTrue(self.bot.thought_word_is_impossible(self.board))
