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
socket.on('botStatus', function(data) {
    var statusSpan = document.getElementById("statusSpan");
    if (data.status === "OK") {
        statusSpan.classList = ['badge bg-success']
        statusSpan.innerHTML = "Connected to website"
        gotPing = true;
    } else {
        statusSpan.classList = ['badge bg-danger']
        statusSpan.innerHTML = "Ping failed"
    }
})

setInterval(pingBot, 1000);