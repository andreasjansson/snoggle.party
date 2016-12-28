#todo:
# * ai
# * make skip button submit
# * better message/error graphics

import random
import argparse
from collections import OrderedDict
from functools import wraps
from flask import (
    Flask, session, redirect, url_for, request, render_template, jsonify
)
from flask_socketio import SocketIO, join_room, leave_room
import logging

from snoggle.game import Game
from snoggle.bot_player import BotSelectAction, BotSubmitAction

COLOR_MAP = OrderedDict((
    ('red', '#FF4136'),
    ('green', '#2ECC40'),
    ('purple', '#B10DC9'),
    ('orange', '#FF851B'),
    ('yellow', '#FFDC00'),
    ('teal', '#39CCCC'),
))


app = Flask(__name__, static_url_path='')
app.secret_key = 'super super secret key'
socketio = SocketIO(app) #, logger=True, engineio_logger=True)
games = {}


def background_thread():
    while True:
        for game in games.values():
            if game.playing() and game.turn_out_of_time():
                turn_time_out(game)
        socketio.sleep(0.5)


socketio.start_background_task(target=background_thread)


def require_game(started=True, emit=None, turn=False, playing=False):
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
                    broadcast_emit_game(game, template=emit)

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
        game = games[session['game_id']]
        if 'color' in session and session['color'] not in game.players:
            # session variables hanging over from quit game
            del session['game_id']
            del session['color']
        else:
            if game.started():
                return redirect(url_for('main'))
            else:
                return redirect(url_for('wait'))

    error = session.pop('error', None)
    return render_template('index.html', colors=COLOR_MAP.keys(), color_map=COLOR_MAP, error=error)


@app.route('/join', methods=['POST'])
def join():
    game_id = request.form['game-id']
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
        game = Game(game_id, is_deterministic=is_deterministic)
        games[game_id] = game

        if 'turn_time' in session:
            game.max_turn_time = session['turn_time']

        if 'num_turns' in session:
            game.num_turns = session['num_turns']

        if 'board_width' in session:
            game.width = session['board_width']

    # these three lines are "atomic", must always happen together
    game.add_human_player(color)
    session['color'] = color
    session['game_id'] = game_id

    broadcast_emit_game(game, 'wait')

    return redirect(url_for('wait'))


@app.route('/wait', methods=['GET', 'POST'])
@require_game(False)
def wait(game, player):
    if game.started():
        return redirect(url_for('main'))

    state = game_state(game, player)
    return render_template('wait.html', **state)


@app.route('/add-bot', methods=['GET', 'POST'])
@require_game(False)
def add_bot(game, player):
    if game.started():
        return redirect(url_for('main'))

    available_colors = set(COLOR_MAP.keys()) - set(game.players.keys())
    color = random.sample(available_colors, 1)[0]
    game.add_bot(color)
    state = game_state(game, player)
    return redirect(url_for('wait'))


@app.route('/delete-bot', methods=['GET', 'POST'])
@require_game(False)
def delete_bot(game, player):
    if game.started():
        return redirect(url_for('main'))

    color = request.args['color']
    game.delete_bot(color)

    state = game_state(game, player)
    return redirect(url_for('wait'))


@app.route('/options', methods=['GET'])
@require_game(False, emit='wait')
def options(game, player):
    if game.started():
        return redirect(url_for('main'))

    args = request.args

    if 'turn-time' in args:
        turn_time = int(args['turn-time'])
        if turn_time in [10, 20, 40, 60]:
            game.max_turn_time = turn_time
            session['turn_time'] = turn_time
        else:
            player.error = 'Invalid turn time'

    if 'num-turns' in args:
        num_turns = int(args['num-turns'])
        if num_turns in [1, 2, 3, 4, 5]:
            game.num_turns = num_turns
            session['num_turns'] = num_turns
        else:
            player.error = 'Invalid num turns'

    if 'board-width' in args:
        board_width = int(args['board-width'])
        if board_width in [4, 5]:
            game.width = board_width
            session['board_width'] = board_width
        else:
            player.error = 'Invalid board width'

    return redirect(url_for('wait'))


@app.route('/start', methods=['GET', 'POST'])
@require_game(False)
def start(game, player):
    if len(game.players) < 2:
        player.error = 'Need at least two players to play'
        return redirect(url_for('wait'))

    if game.playing():
        return redirect(url_for('main'))

    game.start_round()
    for p in game.human_players():
        if p.sid:
            socketio.emit('start', room=p.sid)

    return redirect(url_for('main'))


@app.route('/game', methods=['GET', 'POST'])
@require_game()
def main(game, player):
    session['turn_time'] = game.max_turn_time
    session['num_turns'] = game.num_turns
    session['board_width'] = game.width

    state = game_state(game, player)
    return render_template('main.html', **state)


@app.route('/select', methods=['POST'])
@require_game(emit='main', turn=True, playing=True)
def select(game, player):
    x, y = request.form['position'].split('|')[1].split(',')
    x, y = int(x), int(y)

    game.player_select_cell(player, x, y)

    return redirect(url_for('main'))


@app.route('/select-ajax', methods=['POST'])
@require_game(turn=True, playing=True)
def select_ajax(game, player):
    x, y = request.form['position'].split('|')[1].split(',')
    x, y = int(x), int(y)

    game.player_select_cell(player, x, y)

    return jsonify({
        'word': (player.guess.letters()
                 if player.is_guessing
                 else player.word.letters()),
        'board_html': render_template('board.html',
                                      **game_state(game, player))
    })


@app.route('/submit', methods=['GET', 'POST'])
@require_game(emit='main', turn=True, playing=True)
def submit(game, player):
    if len(player.guess if player.is_guessing else player.word) == 0:
        player.error = 'You have\'t made a word yet'
        return redirect(url_for('main'))

    game.check_word_and_guess(player)
    return redirect(url_for('main'))


@app.route('/start-guessing')
@require_game(emit='main', turn=True, playing=True)
def start_guessing(game, player):
    player.start_guessing()

    return redirect(url_for('main'))


@app.route('/clear')
@require_game(emit='main', turn=True, playing=True)
def clear(game, player):
    if player.is_guessing:
        player.clear_guess()
    else:
        player.clear_word()

    return redirect(url_for('main'))


@app.route('/pass')
@require_game(emit='main', turn=True, playing=True)
def pass_turn(game, player):
    player.clear_word()
    game.next_turn()
    return redirect(url_for('main'))


@app.route('/next-round')
@require_game(emit='main')
def next_round(game, player):
    game.start_round()
    return redirect(url_for('main'))


@app.route('/quit')
@require_game(started=False)
def quit_game(game, player):
    game.end()
    del games[game.game_id]
    del session['game_id']
    del session['color']

    for p in game.human_players():
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


def turn_time_out(game):
    if game.player_turn().is_bot:
        take_bot_action(game, game.player_turn())
    else:
        game.check_word_and_guess(game.player_turn(), end_of_turn=True)

    game.next_turn()

    #print 'turn time out'

    with app.app_context():
        broadcast_emit_game(game, 'main')


def take_bot_action(game, bot):
    attempt = 0
    for _ in range(100):
        if attempt >= bot.num_attempts:
            return

        action = bot.take_action(game.board_view(bot))

        #print 'ACTION', action

        if action is None:
            attempt +=1
            continue

        if isinstance(action, BotSelectAction):
            success = game.player_select_cell(bot, action.x, action.y)
            if not success:
                bot.action_failed()

        elif isinstance(action, BotSubmitAction):
            success = game.check_word_and_guess(bot, end_of_turn=True)
            if success:
                bot.submit_successful()
                return
            else:
                bot.action_failed()
                attempt += 1


def broadcast_emit_game(game, template):
    for p in game.human_players():
        if p.sid:
            if p.color == 'green':
                print '>>>>>>>> EMITTING GAME UPDATE'
            socketio.emit('game updated', {
                'html': render_template(
                    '%s.html' % template, **game_state(game, p))
                }, room=p.sid)


def game_state(game, player):
    return {
        'players': sorted(
            [p.to_visible_dict() for p in game.players.values()],
            key=lambda p: p['wins'], reverse=True
        ),
        'other_colors': [p.color for p in game.players.values()
                         if p != player],
        'player': player,
        'word_length': len(player.guess if player.is_guessing else player.word),
        'board_view': (game.full_board_view()
                       if game.ended()
                       else game.board_view(player)),
        'turn': game.player_turn(),
        'is_players_turn': game.player_turn() == player,
        'results': game.gather_results() if game.ended() else None,
        'ended': game.ended(),
        'turns_left': game.turns_left,
        'num_players': len(game.players),
        'game_id': game.game_id,
        'message': player.pop_message(),
        'color_map': COLOR_MAP,
        'turn_time_left': '%.1f' % game.turn_time_left_display(),
        'turn_time_percent': round(100.0 * game.turn_time_left_display() /
                                   game.max_turn_time, 2),
        'turn_time_total': game.max_turn_time,
        'board_width': game.width,
        'num_turns': game.num_turns,
        'dice_width_percent': round(100.0 / game.width, 2),
    }


def parse_args():
    parser = argparse.ArgumentParser(description='Snoggle game')
    parser.add_argument('--debug', default=False, action='store_true')
    parser.add_argument('--deterministic-board', default=False,
                        action='store_true')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    app.debug = args.debug
    port = 5000 if args.debug else 80
    is_deterministic = args.deterministic_board
    socketio.run(app, host='0.0.0.0', port=port)
