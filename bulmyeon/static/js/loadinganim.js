document.addEventListener('DOMContentLoaded', function () {
    var submitButton = document.getElementById('submitButton');
    submitButton.addEventListener('click', function () {
        var form = document.getElementById('uploadForm');
        if (form.checkValidity()) {
            showUploading();
            form.submit();
        } else {
            form.reportValidity();
        }
    });
});

function showUploading() {
    var uploadButton = document.querySelector('.submit-button');
    uploadButton.textContent = 'Please wait…';
    uploadButton.setAttribute('aria-busy', 'true');
    uploadButton.className = 'girl-button2 please-wait-button';
}