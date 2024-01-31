function showPopup(message) {
    var dialog = $('<dialog open>' +
        '<article class="dialog-main">' +
        '<li>' + message + '</li>' +
        '</article>' +
        '</dialog>');

    $('body').append(dialog);

    dialog.show();

    setTimeout(function () {
        dialog.hide();
        dialog.remove(); 
    }, 1500);
}

var messagesElement = document.querySelector('.messages');
if (messagesElement) {
    var messages = messagesElement.querySelectorAll('li');
    messages.forEach(function (messageElement) {
        showPopup(messageElement.innerHTML);
    });
}
