/*
 *   Copyright (c) 2021 George Keylock
 *   All rights reserved.
 */
var socket = io({ transports: ["websocket"] });

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
                socket.emit('settingsChange', { key: element.id, value: element.value, guild_id: location.href.substring(location.href.lastIndexOf('/') + 1) });
            }
        };
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
        socket.emit('updateGuildCommands', { guild_id: location.href.substring(location.href.lastIndexOf('/') + 1), enabled: enabled, disabled: disabled })
    });
    socket.on('sendGuildDisabledCommands', data => {
        data.disabledCommands.forEach(element => {
            var checkbox = document.getElementById(element);
            checkbox.removeAttribute('checked')
        });
    });
    socket.emit('getGuildDisabledCommands', { guild_id: location.href.substring(location.href.lastIndexOf('/') + 1) });
});

function getAllCommands() {
    socket.emit('getAllCommands');
}

socket.on('allCommands', function (data) {
    console.log(data);
});