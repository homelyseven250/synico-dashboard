refreshGuildsBtn = document.getElementById("refreshGuildsBtn");
refreshGuildsBtn.addEventListener("click", function () {
    // xhr request to refresh guilds
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/refreshGuilds", true);
    xhr.send();
    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4 && xhr.status == 200) {
            location.reload();
        }
    }
}
);

