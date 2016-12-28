var socket;
var timer;
var refreshFrequency = 100;
var timeLeft = 0;

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
    console.log(data);

    var word = data.word.toUpperCase();
    $('#board').html(data.board_html);
    $('#your-word').text(word);
    if (word.length > 0) {
        $('#submit-word').removeAttr('disabled');
    }
}

function selectLetter(e) {
    e.preventDefault();

    var $button = $($(e.target).closest('button'));

    if ($button.attr('disabled')) {
        return false;
    }

    $button.attr('disabled', 'disabled');
    $button.addClass('animate-spin');

    $.post('/select-ajax', {'position': $button.attr('value')},
           handleSelectResponse);

    return false;
}

function handleGameUpdate(data) {
    console.log('game updated')
    replaceHtml(data.html, 'wrapper');
    updateCountdownTime();
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

function handleGameQuit(data) {
    alert(data.color + ' just quit the game');
    location.href = '/';
}

function ajaxClick(e) {
    e.preventDefault();

    var $a = $(e.target).closest('a');
    $('img', $a).addClass('animate-spin');

    $.get($a.attr('href'));

    return false;
}

function preloadImage(url) {
    var img = new Image();
    img.src = url;
}


function preloadAllLetters() {
    var colors = ['red', 'green', 'purple', 'orange', 'yellow', 'teal'];
    var letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
                   'L', 'M', 'N', 'O', 'P', 'Qu', 'R', 'S', 'T', 'U', 'V',
                   'W', 'X', 'Y', 'Z'];
    var folder = '/images/letters-shadow/';
    for (var i = 0; i < letters.length; i ++) {
        var letter = letters[i];
        preloadImage(folder + letter + '.png');
        for (var j = 0; j < colors.length; j ++) {
            var color = colors[j];
            preloadImage(folder + letter + '-with-' + color + '.png');
        }
    }
}

function main() {
    connectSocketIO();

    socket.on('game updated', handleGameUpdate);
    socket.on('game quit', handleGameQuit);

    $('body').on('touchstart mousedown', '#board button', selectLetter);
    $('body').on('click', '#controls a', ajaxClick);
    $('body').on('click', '#next-round', ajaxClick);

    startCountdown();
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

    preloadAllLetters();
}

function index() {
    console.log('here')
}
