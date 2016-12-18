#todo:
# bail / lose single game

from collections import OrderedDict
import datetime
from functools import wraps
from flask import (
    Flask, session, redirect, url_for, request, render_template, send_from_directory
)
from flask_socketio import SocketIO, emit, join_room, leave_room
import logging

from game import Game, MAX_TURN_TIME
import dictionary
from timer import ResettableTimer

COLOR_MAP = OrderedDict((
    ('red', '#FF4136'),
    ('green', '#2ECC40'),
    ('purple', '#B10DC9'),
    ('orange', '#FF851B'),
    ('yellow', '#FFDC00'),
    ('teal', '#39CCCC'),
))


app = Flask(__name__, static_url_path='')
app.logger.setLevel(logging.DEBUG)
app.secret_key = 'super super secret key'
socketio = SocketIO(app) #, logger=True, engineio_logger=True)
socketio.logger = True
games = {}


def require_game(started=True, emit=False, turn=False, playing=False):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            game = None
            try:
                if 'game_id' not in session:
                    return redirect(url_for('index'))
                if session['game_id'] not in games:
                    del session['game_id']
                    return redirect(url_for('index'))
                game = games[session['game_id']]
                if started and not game.started():
                    return redirect(url_for('wait'))
                if session['color'] not in game.players:
                    return redirect(url_for('index'))
                player = game.players[session['color']]

                if turn and game.player_turn() != player:
                    player.error = 'It\'s not your turn!'
                    return redirect(url_for('main'))

                if playing and not game.playing():
                    player.error = 'Not playing at the moment'
                    return redirect(url_for('main'))

                return f(game, player, *args, **kwargs)
            finally:
                if emit and game:
                    broadcast_emit_game(game)

        return wrapper
    return decorator


def require_game_socket(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'game_id' not in session:
            return
        if session['game_id'] not in games:
            return
        game = games[session['game_id']]
        player = game.players[session['color']]
        room = player.sid if player.sid else None

        return f(game, player, room, *args, **kwargs)
    return wrapper


@app.route('/')
def index():
    if 'game_id' in session and session['game_id'] in games:
        return redirect(url_for('main'))

    error = session.pop('error', None)
    return render_template('index.html', colors=COLOR_MAP.keys(), color_map=COLOR_MAP, error=error)


@app.route('/join', methods=['POST'])
def join():
    game_id = request.form['game_id']

    if not game_id:
        session['error'] = 'Missing Game ID'
        return redirect(url_for('index'))

    color = request.form['color']

    if color not in COLOR_MAP:
        session['error'] = '%s in not a valid color' % color
        return redirect(url_for('index'))

    if game_id in games:
        game = games[game_id]
        if game.started():
            session['error'] = 'Game has already started'
            return redirect(url_for('index'))

        if color in game.players:
            session['error'] = '%s is already taken' % color
            return redirect(url_for('index'))

        game = games[game_id]
    else:
        game = Game(game_id)
        game.timer = ResettableTimer(MAX_TURN_TIME, turn_time_out, (game, ))

        games[game_id] = game

    game.add_player(color)

    session['color'] = color
    session['game_id'] = game_id

    for p in game.players.values():
        if p.sid:
            socketio.emit('player joined', {
                'html': render_template(
                    'wait.html', **game_state(game, p))
                }, room=p.sid)

    return redirect(url_for('wait'))


@app.route('/wait', methods=['GET', 'POST'])
@require_game(False)
def wait(game, player):
    state = game_state(game, player)

    if game.started():
        return redirect(url_for('main'))

    return render_template('wait.html', **state)


@app.route('/start', methods=['POST'])
@require_game(False)
def start(game, player):
    if len(game.players) < 2:
        player.error = 'Need at least two players to play'
        return redirect(url_for('wait'))

    game.start_round()
    for p in game.players.values():
        if p.sid:
            socketio.emit('start', room=p.sid)

    return redirect(url_for('main'))


@app.route('/game', methods=['GET', 'POST'])
@require_game()
def main(game, player):
    state = game_state(game, player)
    return render_template('main.html', **state)


@app.route('/select', methods=['POST'])
@require_game(emit=True, turn=True, playing=True)
def select(game, player):
    x, y = request.form['position'].split('|')[1].split(',')
    x, y = int(x), int(y)

    cell = game.board[(x, y)]

    if player.is_guessing:
        player.guess.append(cell)

        if (x, y) in player.seen_positions:
            return redirect(url_for('main'))

    else:
        if not player.is_adjacent_to_last_position((x, y)):
            return redirect(url_for('main'))

        player.seen_positions.add((x, y))

        if not game.player_at(x, y):
            player.last_position = (x, y)
            player.word.append(cell)

    return redirect(url_for('main'))


@app.route('/submit', methods=['POST'])
@require_game(emit=True, turn=True, playing=True)
def submit(game, player):
    if len(player.guess if player.is_guessing else player.word) == 0:
        player.error = 'You have\'t made a word yet'
        return redirect(url_for('main'))

    check_word_and_guess(game, player)
    return redirect(url_for('main'))


@app.route('/start-guessing')
@require_game(emit=True, turn=True, playing=True)
def start_guessing(game, player):
    player.start_guessing()

    return redirect(url_for('main'))


@app.route('/clear')
@require_game(emit=True, turn=True, playing=True)
def clear(game, player):
    if player.is_guessing:
        player.clear_guess()
    else:
        player.clear_word()

    return redirect(url_for('main'))


@app.route('/pass')
@require_game(emit=True, turn=True, playing=True)
def pass_turn(game, player):
    player.clear_word()
    game.next_turn()
    return redirect(url_for('main'))


@app.route('/next-round')
@require_game()
def next_round(game, player):
    game.start_round()
    broadcast_emit_game(game)
    return redirect(url_for('main'))


@app.route('/quit')
@require_game(emit=True, started=False)
def quit_game(game, player):
    game.end()
    del games[game.game_id]
    del session['game_id']
    del session['color']

    for p in game.players.values():
        if p.sid and p != player:
            socketio.emit('game quit', {'color': player.color}, room=p.sid)

    return redirect(url_for('index'))


@app.route('/<path:path>')
def static_proxy(path):
    return app.send_static_file(path)


@socketio.on('connect')
@require_game_socket
def socket_connect(game, player, room):
    join_room(request.sid)
    player.sid = request.sid


@socketio.on('disconnect')
@require_game_socket
def socket_disconnect(game, player, room):
    leave_room(request.sid)
    print('Client disconnected')


def check_word_and_guess(game, player, end_of_turn=False):
    word = player.guess if player.is_guessing else player.word

    if len(word) == 0:
        return

    letters = word.letters().upper()
    score = dictionary.score(word)

    if player.is_guessing:
        word_player = game.player_with_word(word)

        if player.color in word.previous_owners:
            player.set_error('You owned that before!')
            player.clear_guess()

        if word_player:
            player.steal_word(word_player, word)
            player.set_message('You guessed %s\'s word %s (%d points)!' % (
                word_player.color, letters, score))
            word_player.set_message('%s guessed your word %s' % (
                player.color.capitalize(), letters))
            game.next_turn()

        else:
            if not end_of_turn:
                player.set_error('Nope, no one has that word!')
                player.clear_guess()

    else:
        if dictionary.contains(word):
            player.add_word(word)
            player.set_message('%s: %d points!' % (letters, score))
            if not end_of_turn:
                game.next_turn()

        else:
            player.clear_word()
            if not end_of_turn:
                player.set_error('%s is not a word' % letters)


def turn_time_out(game):
    check_word_and_guess(game, game.player_turn(), end_of_turn=True)
    game.next_turn()

    with app.app_context():
        broadcast_emit_game(game)


def broadcast_emit_game(game):
    for p in game.players.values():
        if p.sid:
            socketio.emit('game updated', {
                'html': render_template(
                    'main.html', **game_state(game, p))
                }, room=p.sid)


def game_state(game, player):
    print player.color, player.message

    return {
        'players': sorted(
            [p.to_visible_dict() for p in game.players.values()],
            key=lambda p: p['wins'], reverse=True
        ),
        'other_colors': [p.color for p in game.players.values()
                         if p != player],
        'player': player,
        'word_length': len(player.guess if player.is_guessing else player.word),
        'board_view': (game.full_board_view_dict()
                       if game.ended()
                       else game.board_view_dict(player)),
        'turn': game.player_turn(),
        'is_players_turn': game.player_turn() == player,
        'results': game.gather_results() if game.ended() else None,
        'ended': game.ended(),
        'turns_left': game.turns_left,
        'num_players': len(game.players),
        'game_id': game.game_id,
        'message': player.pop_message(),
        'color_map': COLOR_MAP,
        'turn_time_left': '%.1f' % game.turn_time_left(),
        'turn_time_percent': int(100 * game.turn_time_left() / MAX_TURN_TIME),
        'turn_time_total': MAX_TURN_TIME,
    }


app.debug = True
socketio.run(app, host='0.0.0.0')
