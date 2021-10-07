/*
 *   Copyright (c) 2021 George Keylock
 *   All rights reserved.
 */

var gotPing;
const socket = io()
function pingBot() {
    if (gotPing != true) {
        statusSpan.classList = ['badge bg-danger']
        statusSpan.innerHTML = "Ping failed"
    }
    socket.emit('pingBot');
    gotPing = false;
}
socket.on('botStatus', function (data) {
    var statusSpan = document.getElementById("statusSpan");
    if (data.status === "OK") {
        statusSpan.classList = ['badge bg-success']
        statusSpan.innerHTML = "Connected to website"
        gotPing = true;
    } else {
        statusSpan.classList = ['badge bg-danger']
        statusSpan.innerHTML = "Ping failed"
    }
});

socket.on('disabledCommands', function (data) {
    var disabledCommandsDiv = document.getElementById('disabled-commands');
    data.disabledCommands.forEach(element => {
        var enableButton = document.createElement('button');
        enableButton.setAttribute('class', 'btn btn-primary');
        enableButton.innerText = `Enable ${element.name}`;
        enableButton.addEventListener('click', function () {
            socket.emit('enableCommand', element)
        });
        disabledCommandsDiv.appendChild(enableButton);
        disabledCommandsDiv.appendChild(document.createElement('br'))
    });

});



setInterval(pingBot, 1000);

window.addEventListener('DOMContentLoaded', function () {
    var triggerCommandSyncBtn = document.getElementById('triggerCommandSync');
    triggerCommandSyncBtn.addEventListener('click', function () {
        socket.emit('getAllCommands');
    });
    var disabledCommandSyncBtn = document.getElementById('disabledCommandSync');
    disabledCommandSyncBtn.addEventListener('click', function () {
        socket.emit('getDisabledCommands');
    });
});
