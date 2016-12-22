var socket;
var timer;
var refreshFrequency = 100;
var timeLeft = 0;
var explosionImageSrc = '/images/explosion.png';

preloadExplosionImage();

function preloadExplosionImage() {
    var img = new Image();
    img.src = explosionImageSrc;
}

function replaceHtml(html, id) {
    var body = '<div id="body-mock">' + html.replace(/^[\s\S]*<body.*?>|<\/body>[\s\S]*$/ig, '') + '</div>';
    var $body = $(body);
    var innerHtml = $body.find('#' + id).html();
    $('#' + id).html(innerHtml);
}

function connectSocketIO() {
    socket = io.connect('http://' + document.domain + ':' + location.port + '/');
}

function handleSelectResponse(data) {
    var word = data.word.toUpperCase();
    $('#board').html(data.board_html);
    $('#your-word').text(word);
    if (word.length > 0) {
        $('#submit-word').removeAttr('disabled');
    }
}

function selectLetter(e) {
    var $button = $($(e.target).closest('button'));

    if ($button.attr('disabled')) {
        return false;
    }

    $button.attr('disabled', 'disabled');
    $button.addClass('animate-blur');

    $.post('/select-ajax', {'position': $button.attr('value')},
           handleSelectResponse);

    return false;
}

function handleGameUpdate(data) {
    console.log('game updated')
    replaceHtml(data.html, 'wrapper');
    updateCountdownTime();
    setupGuessButton();

    var $message = $('#message');
    if ($message.length) {
        $message.remove();
        showExplosion($message.html());
    }

    handleError();
}

function handleError() {
    var $error = $('#error');
    if ($error.length) {
        $error.remove();
        showError($error.text());
    }
}

function startCountdown() {
    if (!timer) {
        timer = setInterval(updateCountdown, refreshFrequency);
    }
    updateCountdownTime();
    updateCountdown();
}

function updateCountdown() {
    var $countdown = $('#countdown');
    var turnTime = $countdown.data('total-time');
    timeLeft -= 1.0 / (1000. / refreshFrequency)
    fractionLeft = Math.max(0, Math.min(timeLeft / turnTime, 1));
    $countdown.css('width', fractionLeft * 100 + '%');
}

function updateCountdownTime() {
    var $countdown = $('#countdown');
    var staticTimeLeft = $countdown.data('time-left') * 1;
    if (staticTimeLeft > timeLeft) {
        timeLeft = staticTimeLeft;
    }
}

function submitWord() {
    if ($('#submit button').attr('disabled')) {
        return false;
    }
    $.post('/submit');
    return false;
}

function startGuessing() {
    var html = $('#guess-template').html();
    var $wordRow = $('#word-row');
    $wordRow.html(html);
    $('.guess-color').on('click', submitGuess);

    return false;
}

function isGuessing() {
    return $('#guessed-word').length;
}

function submitGuess(e) {
    var $button = $($(e.target).closest('a'));
    var color = $button.data('color');
    var word = $('#guessed-word').text();
    data = {
        'word': word,
        'color': color,
    };
    $.post('/submit-guess', data);

    return false;
}

function setupGuessButton() {
    var $guessButton = $('#guess-button');
    $guessButton.fitText(1.2);
    $guessButton.on('click', startGuessing);
}

function handleGameQuit(data) {
    alert(data.color + ' just quit the game');
    location.href = '/';
}

function showError(error) {
    $('.error').remove();

    var $body = $('body');
    var $div = $('<div>');
    $div.text(error);
    $div.addClass('error');
    $div.css('opacity', 0);
    $div.animate({zoom: 1.3, opacity: 1}, 500)
        .animate({zoom: 1.0}, 500)
        .animate({zoom: 1.3}, 500)
        .animate({zoom: 1.0}, 500)
        .animate({zoom: 1.3}, 500)
        .animate({zoom: .5, opacity: 0}, 500);

    if ($body.width() < 700) {
        $div.css('font-size', '10px');
    }

    $body.prepend($div);
}

function showExplosion(innerHtml) {
    $('.explosion').remove();

    var $body = $('body');
    var $div = $('<div>');
    var $innerDiv = $('<div>');
    $div.append($innerDiv);
    var $img = $('<img>');
    $img.attr('src', explosionImageSrc);

    var width = $body.width();
    var left, top;
    if (width < 700) {
        left = width * .05;
        top = -width * .08;
        width *= 1.5;
        $innerDiv.css('left', width * .25);
        $innerDiv.css('top', width * .1);
        $innerDiv.css('font-size', '10px');
        $innerDiv.css('width', '25%');
    } else {
        left = width * .3;
        top = -width * .05;
        $innerDiv.css('left', width * .26);
        $innerDiv.css('top', width * .1);
        $innerDiv.css('width', '32%');
    }

    $img.css('width', width);
    $div.append($img);
    $div.addClass('explosion');
    $innerDiv.html(innerHtml);
    $div.css('zoom', 3);
    $div.css('right', -500);
    $div.css('opacity', 0);
    $div.animate({zoom: 1, left: left, top: top, opacity: 1}, 300)
        .delay(3000)
        .fadeOut(1)
        .delay(50)
        .fadeIn(1)
        .delay(50)
        .fadeOut(1)
        .delay(50)
        .fadeIn(1)
        .delay(50)
        .fadeOut(1)
        .delay(50)
        .fadeIn(1)
        .delay(50)
        .fadeOut(1);
    $body.prepend($div);
}

function ajaxClick(e) {
    var $a = $(e.target).closest('a');

    $.get($a.attr('href'));

    return false;
}

function main() {
    connectSocketIO();

    socket.on('game updated', handleGameUpdate);
    socket.on('game quit', handleGameQuit);

    $('body').on('click', '#board button', selectLetter);
    $('body').on('click', '#submit', submitWord);
    $('body').on('click', '#controls a', ajaxClick);
    $('body').on('click', '#next-round', ajaxClick);

    startCountdown();
    setupGuessButton();
    handleError();
}

function wait() {
    connectSocketIO();

    socket.on('game quit', handleGameQuit);

    socket.on('game updated', function (data) {
        replaceHtml(data.html, 'wrapper');
    });
    socket.on('start', function () {
        location.href = '/game';
    });

    $('body').on('click', '.options a', ajaxClick);

    handleError();
}

function index() {
    console.log('here')
    handleError();
}
