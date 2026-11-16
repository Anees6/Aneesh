
function updateStatus() {
    const now = new Date();

    const time = new Intl.DateTimeFormat("en-GB", {
        timeZone: "Asia/Kolkata",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
    }).format(now);

    const parts = new Intl.DateTimeFormat("en-GB", {
        timeZone: "Asia/Kolkata",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
    }).format(now).split(":");

    const hour = Number(parts[0]);
    const minute = Number(parts[1]);

    const currentMinutes = hour * 60 + minute;

    const status = document.getElementById("status");
    const timeDisplay = document.getElementById("time");

    timeDisplay.textContent = "IST: " + time;

    if (currentMinutes >= 480 && currentMinutes < 1290) {
        status.textContent = "🟢 ഇപ്പോൾ ലഭ്യമാണ്";
        status.className = "status available";
    } else {
        status.textContent = "🔴 ഇപ്പോൾ ലഭ്യമല്ല";
        status.className = "status offline";
    }
}

updateStatus();
setInterval(updateStatus, 1000);
