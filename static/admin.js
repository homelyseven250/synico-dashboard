/*
 *   Copyright (c) 2021 George Keylock
 *   All rights reserved.
 */

var gotPing;
var token;
const socket = io({transports: ["websocket"]})
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
    data.disabledCommands.forEach(element => {
        var checkbox = document.getElementById(element.name);
        checkbox.removeAttribute('checked')
    });

});



setInterval(pingBot, 1000);

window.addEventListener('DOMContentLoaded', function () {
    var triggerCommandSyncBtn = document.getElementById('triggerCommandSync');
    triggerCommandSyncBtn.addEventListener('click', e => {
        socket.emit('getAllCommands',{ token: token});
    });
    var disabledCommandSyncBtn = document.getElementById('disabledCommandSync');
    disabledCommandSyncBtn.addEventListener('click', e => {
        socket.emit('getDisabledCommands' , {token: token});
    });
    var saveSettingsBtn = document.getElementById('saveSettingsBtn');
    saveSettingsBtn.addEventListener('click', e => {
        var checkboxes = document.getElementsByClassName('checkbox-command');
        var enabled = [];
        var disabled = [];
        Array.from(checkboxes).forEach(checkbox => {
            if (checkbox.checked) {
                enabled.push(checkbox.id);
            } else {
                disabled.push(checkbox.id);
            }

        });
        console.log(enabled);
        console.log(disabled);
        socket.emit('updateCommands', {enabled: enabled, disabled: disabled,  token: token})
    });
    socket.emit('getDisabledCommands');
});

socket.on('getToken', function(data) {
    let tokenFetch = fetch(`/api/user/socketiotoken?sid=${socket.id}`, { method: "GET"})
    .then(
        function(response) {
            response.json().then(function(data) {
                console.log(data);
                token = data;
                socket.emit('token', data);
                socket.emit('getGuildDisabledCommands', {  token: token , guild_id: location.href.substring(location.href.lastIndexOf('/') + 1)});
            });
        }
    );
});
