setTimeout(function() {
    var messageBox = document.querySelector('.message-box');
    if (messageBox) {
        messageBox.style.opacity = '0'; 
        setTimeout(function() {
            messageBox.style.display = 'none'; 
        }, 1000); 
    }
}, 5000);