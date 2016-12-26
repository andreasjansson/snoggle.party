from collections import namedtuple
from contextlib import contextmanager
import math
import time
import signal
import subprocess
from unittest2 import TestCase
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, WebDriverException)

TURN_TIME = 20

display = browser1 = browser2 = browser3 = browsers = None


def setUpModule(self):
    global display, browser1, browser2, browser3, browsers

    print 'creating display'
    display = Display(visible=0, size=(800, 600))
    display.start()

    print 'creating browser'
    browser1 = make_browser()
    print 'creating browser'
    browser2 = make_browser()
    print 'creating browser'
    browser3 = make_browser()
    browsers = [browser1, browser2, browser3]

def tearDownModule(self):
    for b in browsers:
        b.quit()
    display.stop()


class TimeoutError(Exception):
    pass

class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)

class SnoggleBrowser(webdriver.Chrome):

    def __init__(self, *args, **kwargs):
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        kwargs['chrome_options'] = options
        webdriver.Chrome.__init__(self, *args, **kwargs)

    def fill_game_id(self, game_id):
        element = self.find_element_by_id('game-id')
        element.send_keys(game_id)

    def click_color(self, color):
        color = self.find_element_by_css_selector(
            '.color-select[value="%s"]' % color)
        color.click()

    def home(self):
        self.get('http://127.0.0.1:80')
        self.wait_for_css_selector('#index-page')

    def wait_for_css_selector(self, selector, timeout=5):
        try:
            WebDriverWait(self, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        except TimeoutException as e:
            print '******************', selector, self.has_element(selector)
            self.get_screenshot_as_file('/opt/snoggle/screenshot-timeout-css.png')
            raise e

    def wait_for_xpath(self, selector, timeout=5):
        try:
            WebDriverWait(self, timeout).until(
                EC.presence_of_element_located((By.XPATH, selector)))
        except TimeoutException as e:
            print '******************', selector, self.has_element(selector)
            self.get_screenshot_as_file('/opt/snoggle/screenshot-timeout-xpath.png')
            raise e

    def wait_for_alert(self, timeout=5):
        try:
            WebDriverWait(self, timeout).until(EC.alert_is_present())
        except TimeoutException as e:
            self.get_screenshot_as_file('/opt/snoggle/screenshot-timeout-alert.png')
            raise e

    def accept_alert(self):
        self.switch_to_alert().accept()

    def join_game(self, color, game_id='foo'):
        self.home()
        self.fill_game_id(game_id)
        self.click_color(color)
        self.wait_for_css_selector('#players')

    def start_game(self):
        self.wait_for_css_selector('#start-game')
        self.find_element_by_css_selector('#start-game').click()
        self.wait_for_css_selector('#scores')

    def has_element(self, selector):
        try:
            self.find_element_by_css_selector(selector)
        except NoSuchElementException:
            return False
        return True

    def get_board(self):
        dices = self.find_elements_by_css_selector('button.dice')
        width = int(math.sqrt(len(dices)))
        board = [[None for x in range(width)] for y in range(width)]

        for dice in dices:
            value = dice.get_attribute('value')
            letter, position = value.split('|')
            x, y = position.split(',')
            x, y = int(x), int(y)
            color = dice.get_attribute('data-color')
            if color == 'NO-COLOR':
                color = None
            board[y][x] = (letter, color)

        return board

    def find_option(self, name, value):
        return self.find_element_by_css_selector(option_selector(name, value))

    def set_option(self, name, value):
        element = self.find_element_by_css_selector(option_selector(name, value))

        if 'selected' not in element.get_attribute('class'):
            element.click()
            self.wait_for_css_selector(option_selector(name, value, True))

    def dice_at(self, x, y):
        return self.find_element_by_css_selector(
            'button[data-position="%d,%d"]' % (x, y))

    def color_at(self, x, y):
        color = self.dice_at(x, y).get_attribute('data-color')
        if color == 'NO-COLOR':
            color = None
        return color

    def letter_at(self, x, y):
        return self.dice_at(x, y).get_attribute('data-letter')

    def click_dice(self, x, y, expected_color=None):
        expected_color = expected_color or self.color()

        self.dice_at(x, y).click()
        self.wait_for_dice(x, y, expected_color)

    def click_dice_sleep(self, x, y):
        self.dice_at(x, y).click()
        time.sleep(1)

    def click_dice_wait_for_letter(self, x, y):
        current_word = self.get_word()
        new_word = current_word + self.letter_at(x, y)
        self.dice_at(x, y).click()
        self.wait_for_word(new_word)

    def wait_for_word(self, word):
        self.wait_for_xpath(
            '//*[@id="your-word" and contains(text(), "%s")]' % word.upper())

    def wait_for_turn_timeout(self, turn_time=TURN_TIME):
        self.wait_for_css_selector('#wait-text', turn_time + 2)

    def wait_for_end_of_game(self, timeout=TURN_TIME):
        self.wait_for_css_selector('#results', timeout)

    def is_ended(self):
        return self.has_element('#results')

    def color(self):
        return self.find_element_by_css_selector('#wrapper').get_attribute(
            'data-player-color')

    def click_word_submit(self):
        self.find_element_by_css_selector('#submit button').click()

    def submit_word(self, *positions):
        for x, y in positions:
            self.click_dice(x, y)

        self.click_word_submit()

    def guess_word(self, *positions):
        for x, y in positions:
            self.click_dice_wait_for_letter(x, y)

        self.click_word_submit()

    def wait_for_dice(self, x, y, color):
        self.wait_for_css_selector(
            '.dice[data-position="%d,%d"][data-color="%s"]' % (x, y, 'NO-COLOR' if color is None else color))

    def wait_for_turn(self):
        self.wait_for_css_selector('#clear-control')

    def scroll_to_bottom(self):
        return self.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def click_clear(self):
        self.find_element_by_css_selector('#clear-control').click()

    def get_word(self):
        return self.find_element_by_id('your-word').text

    def is_guessing(self):
        return self.find_element_by_id('your-word').get_attribute('data-guessing') == 'true'

    def start_guessing(self):
        self.find_element_by_id('start-guessing').click()
        self.wait_for_css_selector('#your-word[data-guessing="true"]')

    def is_active(self):
        return self.has_element('#clear-control')

    def get_results(self):
        results = []
        lis = self.find_elements_by_css_selector('#results .result')
        for li in lis:
            color = li.find_element_by_css_selector('.result-color').text
            total_score = int(
                li.find_element_by_css_selector('.result-total-score').text)
            word_scores = []
            for word_li in li.find_elements_by_css_selector('li'):
                word = word_li.find_element_by_css_selector(
                    '.result-word').text
                score = int(word_li.find_element_by_css_selector(
                    '.result-word-score').text)
                word_scores.append((word, score))

            results.append(Result(color, total_score, word_scores))

        return results

    def get_scores(self):
        scores = []
        div = self.find_element_by_css_selector('#scores')
        for li in div.find_elements_by_css_selector('li'):
            color = li.find_element_by_css_selector('.score-color').text
            wins = int(li.find_element_by_css_selector('.score-wins').text)
            points = int(li.find_element_by_css_selector('.score-points').text)
            scores.append(Score(color, wins, points))

        return scores

    def next_round(self):
        self.find_element_by_id('next-round').click()
        self.wait_for_css_selector('#your-word')

    def quit_game(self):
        self.find_element_by_id('quit-game').click()
        self.wait_for_css_selector('#index-page')


def make_browser(num_attempts=5):
    for i in range(num_attempts):
        try:
            with timeout(seconds=5):
                return SnoggleBrowser()
        except TimeoutError as e:
            print 'browser creation timed out, trying again'
            if i == num_attempts - 1:
                raise e


def start_game(colors=('red', 'teal'), game_id='foo', board_width=5,
               turn_time=TURN_TIME, num_turns=3):
    for b, color in zip(browsers, colors):
        b.join_game(color, game_id)

    browser1.set_option('board-width', board_width)
    browser1.set_option('turn-time', turn_time)
    browser1.set_option('num-turns', num_turns)
    browser1.start_game()


def option_selector(name, value, selected=False):
    return '.options a%s[href="/options?%s=%s"]' % (
        '.selected' if selected else '', name, value)


def get_active_player_browser():
    for b in browsers:
        if b.has_element('#clear-control'):
            return b


def get_inactive_player_browser():
    for b in browsers:
        if b.has_element('#wait-text'):
            return b


Result = namedtuple('Result', 'color score word_scores')
Score = namedtuple('Score', 'color wins points')


class SnoggleTestCase(TestCase):

    def setUp(self):
        print 'starting snoggle process'
        self.snoggle_process = subprocess.Popen(
            ['python', 'snoggle/server.py', '--deterministic'],
            #stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True,
            env={'PYTHONPATH': '.'},
            cwd='/opt/snoggle')
        time.sleep(3)

    def tearDown(self):
        for b in browsers:
            try:
                b.delete_all_cookies()
            except WebDriverException as e:
                print 'failed to clear cookies: %s' % e

        self.snoggle_process.kill()
        time.sleep(1)


class IndexTests(SnoggleTestCase):

    def test_ui_components(self):
        browser1.home()
        self.assertEquals(browser1.title, 'Snoggle')
        self.assertEquals(
            len(browser1.find_elements_by_css_selector('.color-select')), 6)
        self.assertEquals(
            len(browser1.find_elements_by_css_selector('#game-id')), 1)

    def test_join_game_single_player(self):
        browser1.join_game('orange')

        self.assertEquals(browser1.find_element_by_id('game-id').text, 'foo')

        players = browser1.find_elements_by_css_selector(
            '#players li.player')

        self.assertEquals(len(players), 1)
        self.assertEquals(players[0].text, 'orange')

    def test_second_player_join(self):
        browser1.join_game('orange')
        browser2.join_game('teal')

        self.assertEquals(browser2.find_element_by_id('game-id').text, 'foo')

        players1 = browser1.find_elements_by_css_selector(
            '#players li.player')

        players2 = browser2.find_elements_by_css_selector(
            '#players li.player')

        self.assertEquals([p.text for p in players1], ['orange', 'teal'])

        self.assertEquals([p.text for p in players1],
                          [p.text for p in players2])

    def test_join_game_already_started(self):
        start_game()

        browser3.home()
        browser3.fill_game_id('foo')
        browser3.click_color('orange')

        error = browser3.find_elements_by_css_selector('.error')[0]
        self.assertEquals(error.text, 'Game has already started')

    def test_join_game_no_game_id(self):
        browser1.home()
        browser1.click_color('red')

        browser1.wait_for_css_selector('.error')

        error = browser1.find_elements_by_css_selector('.error')[0]
        self.assertEquals(error.text, 'Missing Game ID')

    def test_join_game_existing_color(self):
        browser1.home()
        browser2.home()

        browser1.fill_game_id('foo')
        browser1.click_color('red')

        browser2.fill_game_id('foo')
        browser2.click_color('red')

        browser2.wait_for_css_selector('.error')

        error = browser2.find_elements_by_css_selector('.error')[0]
        self.assertEquals(error.text, 'red is already taken')


class WaitTests(SnoggleTestCase):

    def test_change_options_websocket(self):
        browser1.join_game('red')
        browser2.join_game('green')

        browser1.find_option('turn-time', 10).click()

        browser1.wait_for_css_selector(option_selector('turn-time', 10, True))
        browser2.wait_for_css_selector(option_selector('turn-time', 10, True))

        browser2.find_option('turn-time', 20).click()

        browser1.wait_for_css_selector(option_selector('turn-time', 20, True))
        browser2.wait_for_css_selector(option_selector('turn-time', 20, True))

        self.assertFalse(browser1.find_element_by_css_selector(
            option_selector('turn-time', 10)).get_attribute('selected'))

        self.assertFalse(browser2.find_element_by_css_selector(
            option_selector('turn-time', 10)).get_attribute('selected'))

    def test_start_single_player(self):
        browser1.join_game('red')
        self.assertFalse(browser1.has_element('start-game'))

    def test_start_simultaneously_same_board(self):
        browser1.join_game('red')
        browser2.join_game('green')

        browser1.start_game()
        browser2.get('http://127.0.0.1:80/start')

        board1 = browser1.get_board()
        board2 = browser2.get_board()

        self.assertEquals(board1, board2)

    def test_board_width_4(self):
        browser1.join_game('red')
        browser2.join_game('green')

        browser1.set_option('board-width', 4)
        browser1.start_game()

        self.assertEquals(len(browser1.get_board()), 4)

    def test_board_width_5(self):
        browser1.join_game('red')
        browser2.join_game('green')

        browser1.set_option('board-width', 5)
        browser1.start_game()

        self.assertEquals(len(browser1.get_board()), 5)

    def test_redirect_from_home(self):
        browser1.join_game('red')
        browser1.get('http://127.0.0.1:80')
        browser1.wait_for_css_selector('#wait-page')
        self.assertTrue(browser1.has_element('#wait-page'))



class ActiveInactiveTests(SnoggleTestCase):

    def test_active_player_board_enabled(self):
        start_game()
        active = get_active_player_browser()
        dices = active.find_elements_by_css_selector('.dice')
        self.assertFalse(dices[0].get_attribute('disabled'))

    def test_waiting_player_board_disabled(self):
        start_game()
        inactive = get_inactive_player_browser()
        dices = inactive.find_elements_by_css_selector('.dice')
        self.assertTrue(dices[0].get_attribute('disabled'))

    def test_one_player_active(self):
        start_game(['red', 'teal', 'yellow'])
        active_players = [b for b in browsers if b.is_active()]
        self.assertEquals(len(active_players), 1)

    def test_other_players_waiting(self):
        start_game(['red', 'teal', 'yellow'])
        inactive_players = [b for b in browsers
                          if b.has_element('#wait-text')]
        self.assertEquals(len(inactive_players), 2)


class SelectTests(SnoggleTestCase):

    def test_select_first_letter(self):
        start_game()
        browser1.click_dice(2, 2)
        self.assertEquals(browser1.color_at(2, 2), 'red')
        self.assertEquals(browser1.get_word(), 'T')

    def test_select_adjacent_letter(self):
        start_game()
        browser1.click_dice(2, 2)
        browser1.click_dice(1, 1)
        self.assertEquals(browser1.color_at(1, 1), 'red')
        self.assertEquals(browser1.get_word(), 'TE')

    def test_select_non_adjacent_letter(self):
        start_game()
        browser1.click_dice(2, 2)
        browser1.click_dice_sleep(0, 1)
        self.assertFalse(browser1.color_at(0, 2))
        self.assertEquals(browser1.get_word(), 'T')

    def test_select_other_players_letter(self):
        start_game()
        browser1.submit_word((0, 0), (1, 1), (2, 0), (2, 1), (3, 0))
        browser2.wait_for_turn()
        browser2.click_dice(1, 1, 'red')
        self.assertEquals(browser2.color_at(1, 1), 'red')
        self.assertEquals(browser2.get_word(), '')

    def test_select_while_inactive(self):
        start_game()
        browser2.click_dice_sleep(1, 1)
        self.assertEquals(browser2.color_at(1, 1), None)
        self.assertEquals(browser2.get_word(), 'wait...')

    def test_select_existing_letter(self):
        start_game()
        browser1.click_dice(0, 0)
        browser1.click_dice_sleep(0, 0)
        self.assertEquals(browser1.get_word(), 'P')

    def test_select_existing_letter_next_turn(self):
        start_game(turn_time=40)
        browser1.submit_word((0, 0), (1, 1), (2, 0), (2, 1), (3, 0))

        browser2.wait_for_turn()
        browser2.submit_word((4, 2), (4, 3), (3, 4))

        browser1.wait_for_turn()
        time.sleep(4)
        browser1.click_dice_sleep(1, 1)
        browser1.click_dice_sleep(3, 0)
        self.assertEquals(browser1.get_word(), '')


class ClearTests(SnoggleTestCase):

    def test_clear_selected_letters(self):
        start_game()
        browser1.click_dice(0, 0)
        browser1.click_dice(1, 0)
        self.assertEquals(browser1.color_at(1, 0), 'red')
        self.assertEquals(browser1.get_word(), 'PC')

        browser1.click_clear()
        browser1.wait_for_dice(1, 0, None)

        self.assertEquals(browser1.color_at(1, 0), None)
        self.assertEquals(browser1.get_word(), '')

    def test_clear_other_players_letters(self):
        start_game()
        browser1.submit_word((0, 0), (1, 1), (2, 0), (2, 1), (3, 0))
        browser2.wait_for_turn()
        browser2.click_dice(1, 0)
        browser2.click_dice_sleep(1, 1)
        browser2.click_dice(0, 1)

        self.assertEquals(browser2.get_word(), 'CU')

        browser2.click_clear()
        browser2.wait_for_dice(1, 0, None)

        self.assertEquals(browser2.color_at(1, 0), None)
        self.assertEquals(browser2.color_at(1, 1), 'red')
        self.assertEquals(browser2.color_at(1, 2), None)
        self.assertEquals(browser2.get_word(), '')

    def test_clear_guess_reverts_guess_mode(self):
        start_game()
        browser1.start_guessing()
        browser1.click_dice_wait_for_letter(0, 0)
        browser1.click_dice_wait_for_letter(1, 0)
        self.assertTrue(browser1.is_guessing())

        browser1.click_clear()
        browser1.wait_for_word('')

        self.assertEquals(browser1.get_word(), '')
        self.assertFalse(browser1.is_guessing())


class SubmitOwnWordTests(SnoggleTestCase):

    def test_submit_good_word(self):
        start_game()
        positions = [(0, 0), (1, 1), (2, 0), (2, 1), (3, 0)]
        browser1.submit_word(*positions)
        browser2.wait_for_turn()
        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'red')

        self.assertTrue(browser2.is_active())
        self.assertFalse(browser1.is_active())

    def test_submit_bad_word(self):
        start_game()
        positions = [(0, 0), (1, 0), (2, 0)]
        browser1.submit_word(*positions)
        browser1.wait_for_dice(0, 0, None)
        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), None)

        self.assertTrue(browser1.is_active())
        self.assertFalse(browser2.is_active())

    def test_submit_empty_word(self):
        start_game()
        browser1.click_word_submit()
        self.assertTrue(browser1.is_active())
        self.assertFalse(browser2.is_active())


class GuessSelectTests(SnoggleTestCase):

    def test_guessing_clears_existing_word(self):
        start_game()
        browser1.click_dice(0, 0)
        browser1.start_guessing()
        self.assertEquals(browser1.color_at(0, 0), None)
        self.assertEquals(browser1.get_word(), '')

    def test_guess_doesnt_highlight_dices(self):
        start_game()
        browser1.start_guessing()
        browser1.click_dice_wait_for_letter(0, 0)
        self.assertEquals(browser1.color_at(0, 0), None)
        self.assertEquals(browser1.get_word(), 'P')

    def test_guess_doesnt_have_to_be_adjacent(self):
        start_game()
        browser1.click_dice(0, 0)
        browser1.start_guessing()
        browser1.click_dice_wait_for_letter(2, 0)
        browser1.click_dice_wait_for_letter(2, 2)

        self.assertEquals(browser1.get_word(), 'AT')


class GuessSubmitTests(SnoggleTestCase):

    def test_guess_right_word_right_order(self):
        start_game()
        positions = [(0, 0), (1, 1), (2, 0), (2, 1), (3, 0)]
        browser1.submit_word(*positions)
        browser2.wait_for_turn()
        browser2.start_guessing()
        browser2.guess_word(*positions)
        browser1.wait_for_turn()

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'teal')
            self.assertEquals(browser2.color_at(x, y), 'teal')

    def test_guess_right_word_wrong_order(self):
        start_game()
        positions = [(2, 1), (3, 1), (3, 2), (4, 2)]
        browser1.submit_word(*positions)
        browser2.wait_for_turn()
        browser2.start_guessing()
        browser2.guess_word((2, 1), (3, 2), (3, 1), (4, 2))
        browser1.wait_for_turn()

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'teal')
            self.assertEquals(browser2.color_at(x, y), 'teal')

    def test_guess_right_positions_wrong_word(self):
        start_game(turn_time=40)
        positions = [(1, 2), (1, 1), (2, 2)]
        browser1.submit_word(*positions)
        browser2.wait_for_turn()
        browser2.start_guessing()
        browser2.guess_word((2, 2), (1, 1), (1, 2))
        browser2.wait_for_word('')

        self.assertTrue(browser2.is_active())

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'red')
            self.assertEquals(browser2.color_at(x, y), None)

    def test_guess_empty_word(self):
        start_game()
        browser1.start_guessing()
        browser1.click_word_submit()
        time.sleep(1)

        self.assertTrue(browser1.is_active())
        self.assertEquals(browser1.get_word(), '')

    def test_guess_wrong_word(self):
        start_game()
        positions = [(0, 1), (0, 0)]
        browser1.submit_word(*positions)
        browser2.wait_for_turn()
        browser2.start_guessing()
        browser2.guess_word((0, 4))
        browser2.wait_for_word('')

        self.assertTrue(browser2.is_active())

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'red')
            self.assertEquals(browser2.color_at(x, y), None)

    def test_guess_already_stolen_word(self):
        start_game(turn_time=40)
        positions = [(0, 1), (0, 0)]
        browser1.submit_word(*positions)
        browser2.wait_for_turn()
        browser2.start_guessing()
        browser2.guess_word(*positions)
        browser1.wait_for_turn()

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'teal')
            self.assertEquals(browser2.color_at(x, y), 'teal')

        time.sleep(4) # wait for explosion to disappear

        browser1.start_guessing()
        browser1.guess_word(*positions)
        browser1.wait_for_word('')

        self.assertTrue(browser1.is_active())

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'teal')
            self.assertEquals(browser2.color_at(x, y), 'teal')


class TimeoutTests(SnoggleTestCase):

    def test_timeout_good_guess(self):
        start_game(turn_time=10)
        positions = [(0, 1), (0, 0)]

        browser1.submit_word(*positions)

        browser2.wait_for_turn()
        browser2.start_guessing()
        browser2.click_dice_wait_for_letter(0, 1)
        browser2.click_dice_wait_for_letter(0, 0)
        browser2.wait_for_turn_timeout(10)

        self.assertTrue(browser1.is_active())

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'teal')
            self.assertEquals(browser2.color_at(x, y), 'teal')

    def test_timeout_good_word(self):
        start_game(turn_time=10)
        positions = [(0, 1), (0, 0)]

        browser1.submit_word(*positions)
        browser1.wait_for_turn_timeout(10)

        self.assertTrue(browser2.is_active())

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'red')
            self.assertEquals(browser2.color_at(x, y), None)

    def test_timeout_bad_guess(self):
        start_game(turn_time=10)
        positions = [(0, 1), (0, 0)]

        browser1.submit_word(*positions)

        browser2.wait_for_turn()
        browser2.start_guessing()
        browser2.click_dice_wait_for_letter(0, 0)
        browser2.click_dice_wait_for_letter(0, 1)
        browser2.wait_for_turn_timeout(10)

        self.assertTrue(browser1.is_active())

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), 'red')
            self.assertEquals(browser2.color_at(x, y), None)

    def test_timeout_bad_word(self):
        start_game(turn_time=10)
        positions = [(0, 0), (0, 1)]

        browser1.submit_word(*positions)
        browser1.wait_for_turn_timeout(10)

        self.assertTrue(browser2.is_active())

        for x, y in positions:
            self.assertEquals(browser1.color_at(x, y), None)
            self.assertEquals(browser2.color_at(x, y), None)

    def test_timeout_selected_letters_dont_stick(self):
        start_game(turn_time=10)
        browser1.click_dice(0, 0)
        browser1.wait_for_turn_timeout(10)
        self.assertEquals(browser1.color_at(0, 0), None)

    def test_timeout_found_letters_stick(self):
        start_game(turn_time=10)
        browser1.submit_word((0, 1), (0, 0))
        browser2.wait_for_turn()

        browser2.click_dice(0, 0, 'red')
        browser2.wait_for_turn_timeout(10)

        self.assertEquals(browser1.color_at(0, 0), 'red')
        self.assertEquals(browser2.color_at(0, 0), 'red')


class TurnTests(SnoggleTestCase):

    def test_correct_number_of_turns(self):
        start_game(num_turns=2, turn_time=10)

        browser1.submit_word((0, 0), (1, 1), (2, 2)) #PET

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 0), (3, 0), (3, 1), (3, 2), (2, 1)) #FLOOR

        browser1.wait_for_turn()
        time.sleep(2)
        browser1.submit_word((0, 4), (1, 4), (2, 3)) #QUIT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 2), (4, 3), (3, 4)) #FUR

        browser1.wait_for_end_of_game(10)
        browser2.wait_for_end_of_game(10)

        self.assertTrue(browser1.is_ended())
        self.assertTrue(browser2.is_ended())

    def test_correct_number_of_turns_with_timeout(self):
        start_game(num_turns=3, turn_time=10)

        browser1.submit_word((0, 0), (1, 1), (2, 2)) #PET

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 0), (3, 0), (3, 1), (3, 2), (2, 1)) #FLOOR

        browser1.wait_for_turn()
        time.sleep(2)
        browser1.submit_word((0, 4), (1, 4), (2, 3)) #QUIT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 2), (4, 3), (3, 4)) #FUR

        browser1.wait_for_turn()
        time.sleep(2)
        browser1.submit_word((0, 3), (0, 2)) #ME

        browser2.wait_for_turn()

        browser1.wait_for_end_of_game(12)
        browser2.wait_for_end_of_game(12)

        self.assertTrue(browser1.is_ended())
        self.assertTrue(browser2.is_ended())


class ResultTests(SnoggleTestCase):

    def test_scores(self):
        start_game(num_turns=2, turn_time=10)

        browser1.submit_word((0, 0), (1, 1), (2, 2)) #PET

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 0), (3, 0), (3, 1), (3, 2), (2, 1)) #FLOOR

        browser1.wait_for_turn()
        time.sleep(2)
        browser1.submit_word((0, 4), (1, 4), (2, 3)) #QUIT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 2), (4, 3), (3, 4)) #FUR

        browser1.wait_for_end_of_game(5)
        browser2.wait_for_end_of_game(5)

        expected_results = [
            Result('red', score=17, word_scores=[('QUIT', 12), ('PET', 5)]),
            Result('teal', score=14, word_scores=[('FLOOR', 8), ('FUR', 6)])
        ]

        self.assertEquals(browser1.get_results(), expected_results)
        self.assertEquals(browser2.get_results(), expected_results)

    def test_scores_with_stolen_words(self):
        start_game(num_turns=2, turn_time=10)

        browser1.submit_word((0, 0), (1, 1), (2, 2)) #PET

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 0), (3, 0), (3, 1), (3, 2), (2, 1)) #FLOOR

        browser1.wait_for_turn()
        time.sleep(2)
        browser1.submit_word((0, 4), (1, 4), (2, 3)) #QUIT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.start_guessing()
        browser2.guess_word((0, 0), (1, 1), (2, 2)) #PET

        browser1.wait_for_end_of_game(5)
        browser2.wait_for_end_of_game(5)

        expected_results = [
            Result('teal', score=13, word_scores=[('FLOOR', 8), ('PET', 5)]),
            Result('red', score=12, word_scores=[('QUIT', 12)]),
        ]

        self.assertEquals(browser1.get_results(), expected_results)
        self.assertEquals(browser2.get_results(), expected_results)

    def test_scores_with_failed_words(self):
        start_game(num_turns=2, turn_time=20)

        browser1.submit_word((0, 0), (1, 1), (2, 2)) #PET

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.click_dice(0, 1)
        browser2.click_dice(0, 0, 'red')
        browser2.click_dice(0, 2)
        browser2.click_word_submit()
        browser2.wait_for_word('')

        self.assertTrue(browser2.is_active())

        browser2.click_dice(2, 2, 'red')
        browser2.click_dice(2, 4)
        browser2.wait_for_turn_timeout()

        self.assertEquals(browser2.color_at(2, 4), None)

        browser1.wait_for_turn()
        browser1.submit_word((0, 4), (1, 4), (2, 3)) #QUIT

        browser2.wait_for_turn()
        browser2.click_dice(2, 2, 'red')
        browser2.click_dice(3, 2)
        browser2.start_guessing()
        browser2.click_dice_wait_for_letter(1, 4)
        browser2.click_dice_wait_for_letter(0, 4)

        browser1.wait_for_end_of_game(20)
        browser2.wait_for_end_of_game()

        expected_results = [
            Result('red', score=17, word_scores=[('QUIT', 12), ('PET', 5)]),
            Result('teal', score=0, word_scores=[]),
        ]

        self.assertEquals(browser1.get_results(), expected_results)
        self.assertEquals(browser2.get_results(), expected_results)

    def test_scores_and_wins_updated(self):
        # two games
        start_game(num_turns=2, turn_time=10)

        browser1.submit_word((0, 0), (1, 1), (2, 2)) #PET

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 0), (3, 0), (3, 1), (3, 2), (2, 1)) #FLOOR

        browser1.wait_for_turn()
        time.sleep(2)
        browser1.submit_word((0, 4), (1, 4), (2, 3)) #QUIT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 2), (4, 3), (3, 4)) #FUR

        browser1.wait_for_end_of_game(5)
        browser2.wait_for_end_of_game()

        expected_scores = [Score('red', 1, 17), Score('teal', 0, 14)]

        self.assertEquals(browser1.get_scores(), expected_scores)
        self.assertEquals(browser2.get_scores(), expected_scores)

        browser1.next_round()

        browser1.submit_word((2, 0), (1, 0), (1, 1)) #ACE

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 0), (3, 0), (3, 1), (3, 2), (2, 1)) #FLOOR

        browser1.wait_for_turn()
        time.sleep(2)
        browser1.submit_word((0, 4), (1, 4), (2, 3)) #QUIT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((0, 1), (0, 0)) #UP

        browser1.wait_for_end_of_game(5)
        browser2.wait_for_end_of_game()

        expected_scores = [Score('red', 2, 34), Score('teal', 0, 26)]

        self.assertEquals(browser1.get_scores(), expected_scores)
        self.assertEquals(browser2.get_scores(), expected_scores)

    def test_tie(self):
        start_game(num_turns=2, turn_time=10)

        browser1.submit_word((0, 0), (1, 1), (1, 2), (2, 2)) #PENT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 0), (3, 0), (3, 1), (3, 2), (2, 1)) #FLOOR

        browser1.wait_for_turn()
        time.sleep(2)
        browser1.submit_word((0, 4), (1, 4), (2, 3)) #QUIT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 2), (4, 3), (3, 4), (2, 4)) #FURY

        browser1.wait_for_end_of_game(5)
        browser2.wait_for_end_of_game()

        expected_scores = [Score('red', 1, 18), Score('teal', 1, 18)]

        self.assertEquals(browser1.get_scores(), expected_scores)
        self.assertEquals(browser2.get_scores(), expected_scores)


class AnotherRoundTests(SnoggleTestCase):

    def test_start_new_round(self):
        start_game(num_turns=2, turn_time=10)

        browser1.submit_word((0, 0), (1, 1), (1, 2), (2, 2)) #PENT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 0), (3, 0), (3, 1), (3, 2), (2, 1)) #FLOOR

        browser1.wait_for_turn()
        time.sleep(2)
        browser1.submit_word((0, 4), (1, 4), (2, 3)) #QUIT

        browser2.wait_for_turn()
        time.sleep(2)
        browser2.submit_word((4, 2), (4, 3), (3, 4), (2, 4)) #FURY

        browser1.wait_for_end_of_game(5)
        browser2.wait_for_end_of_game()

        self.assertFalse(browser1.is_active())
        self.assertFalse(browser2.is_active())

        browser1.next_round()

        self.assertTrue(browser1.is_active())
        self.assertFalse(browser2.is_active())
        self.assertTrue(browser2.has_element('#wait-text'))


class QuitTests(SnoggleTestCase):

    def test_quit_on_wait_screen(self):
        browser1.join_game('red')
        browser2.join_game('teal')

        browser1.quit_game()

        self.assertEquals(browser1.current_url, 'http://127.0.0.1/')

        browser2.wait_for_alert()
        browser2.accept_alert()
        browser2.wait_for_css_selector('#index-page')

        self.assertEquals(browser2.current_url, 'http://127.0.0.1/')

    def test_quit_on_game_screen(self):
        start_game()

        browser1.quit_game()

        self.assertEquals(browser1.current_url, 'http://127.0.0.1/')

        browser2.wait_for_alert()
        browser2.accept_alert()
        browser2.wait_for_css_selector('#index-page')

        self.assertEquals(browser2.current_url, 'http://127.0.0.1/')

    def test_quit_can_restart(self):
        start_game()

        browser1.quit_game()

        browser2.wait_for_alert()
        browser2.accept_alert()
        browser2.wait_for_css_selector('#index-page')

        start_game()

        self.assertTrue(browser1.is_active())
