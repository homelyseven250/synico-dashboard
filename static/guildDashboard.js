/*
 *   Copyright (c) 2021 George Keylock
 *   All rights reserved.
 */
var socket = io();

// function processWarning(data) {
//     var reportsDiv = document.getElementById('warnings');
//     var warningElement = document.createElement('div');
//     warningElement.innerHTML = data.innerHTML;
//     reportsDiv.appendChild(warningElement);
//     var cardBody = warningElement.children[0].children[0];
// }

// socket.on('warning', function (data) {
//     processWarning(data);
// });

// socket.on('warnings', function (data) {
//     for (i = 0; i++; i<data.warnings.length) {
//         processWarning(data.warnings[i]);
//     }
// })
document.addEventListener('DOMContentLoaded', function (e) {
    var basicFormSubmit = document.getElementById('basic-submit');
    var basicForm = document.getElementById('basic-form');
    basicFormSubmit.addEventListener('click', function (e) {
        for (let element of basicForm.children[0].children) {
            if (element.getAttribute('type') == 'text') {
                socket.emit('settingsChange', {key:element.id, value:element.value});
            }
        };
    });
});
