var socket;
var timer;
var refreshFrequency = 100;
var timeLeft = 0;
var refreshHandler;
var preloadedImages = [];

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
    replaceHtml(data.html, 'wrapper');
    refreshHandler();
}

function mainRefreshHandler() {
    updateCountdownTime();
}

function waitRefreshHandler() {
    preloadLetters(getWaitingColors());
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

function handleAjaxGetResponse(data) {
    replaceHtml(data, 'wrapper');
    refreshHandler();
}

function ajaxGet(e) {
    e.preventDefault();

    var $a = $(e.target).closest('a');
    $('img', $a).addClass('animate-spin');

    $.get($a.attr('href'), handleAjaxGetResponse);

    return false;
}

function preloadImage(url) {
    if (preloadedImages.indexOf(url) == -1) {
        var img = new Image();
        console.log(url);
        img.src = url;
        preloadedImages.push(url);
    }
}

function preloadLetters(colors) {
    var letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
                   'L', 'M', 'N', 'O', 'P', 'Qu', 'R', 'S', 'T', 'U', 'V',
                   'W', 'X', 'Y', 'Z'];
    var folder = '/images/letters-shadow/';
    for (var i = 0; i < letters.length; i ++) {
        var letter = letters[i];
        for (var j = 0; j < colors.length; j ++) {
            var color = colors[j];
            if (color == 'NO-COLOR') {
                preloadImage(folder + letter + '.png');
            } else {
                preloadImage(folder + letter + '-with-' + color + '.png');
            }
        }
    }
}

function getWaitingColors() {
    return $('.player-color').map(function(i, el) {
        return $(el).text();
    });
}

function preloadImages() {
    var colors = getWaitingColors();
    console.log('>>>>>>>>>', colors);
    colors.push('NO-COLOR');
    preloadLetters(colors);
    preloadImage('/images/blowfish.png');
    preloadImage('/images/shark.png');
    preloadImage('/images/background.jpg');
}

function commonSetup(refreshHandler_) {
    refreshHandler = refreshHandler_;
    connectSocketIO();

    socket.on('game updated', handleGameUpdate);
    socket.on('game quit', handleGameQuit);

    $('body').on('click', '.ajax-get', ajaxGet);
}

function main() {
    commonSetup(mainRefreshHandler);

    $('body').on('touchstart mousedown', '#board button', selectLetter);

    startCountdown();
}

function wait() {
    commonSetup(waitRefreshHandler);

    socket.on('start', function () {
        location.href = '/game';
    });

    window.setTimeout(preloadImages, 250);
}

function index() {

}
