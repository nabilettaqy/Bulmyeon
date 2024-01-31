let hideInfoTimeout;
let hideGirl2InfoTimeout;

function showInfo() {
    clearTimeout(hideInfoTimeout);
    document.getElementById('girl-info').style.opacity = 1;
    document.getElementById('girl1-link').style.pointerEvents = 'initial';
}

function hideInfo() {
    hideInfoTimeout = setTimeout(function() {
        document.getElementById('girl-info').style.opacity = 0;
        document.getElementById('girl1-link').style.pointerEvents = 'none';
    }, 1500);
}

function showGirl2Info() {
    clearTimeout(hideGirl2InfoTimeout);
    document.getElementById('girl2-info').style.opacity = 1;
    document.getElementById('girl2-link').style.pointerEvents = 'initial';
}

function hideGirl2Info() {
    hideGirl2InfoTimeout = setTimeout(function() {
        document.getElementById('girl2-info').style.opacity = 0;
        document.getElementById('girl2-link').style.pointerEvents = 'none';
    }, 1500);
}