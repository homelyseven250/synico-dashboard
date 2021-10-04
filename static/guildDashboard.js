var socket = io();

socket.on('reportEvent', function (data) {
 var reportsDiv = document.getElementById('reports');
 var reportElement = document.createElement('div');
 reportElement.innerHTML = data.innerHTML;
 reportsDiv.appendChild(reportElement);
 var cardBody = reportElement.children[0].children[0];
 for (var i = 0; i < cardBody.children.length; i++) {
 if (cardBody.children[i].classList.contains('ban')) {
 cardBody.children[i].addEventListener('click', function (e) {
 socket.emit('ban', {
 user: data.user,
 reason: e.target.innerText
 });
 }
 );}
 }
}
);

setTimeout(function () {
 socket.emit('ping');
}, 5000);