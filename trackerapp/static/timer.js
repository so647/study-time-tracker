let timer;
let isRunning = false;
let startTime = null; 
let elapsedSeconds = 0;

const display = document.getElementById("display");
const startButton = document.getElementById("start");
const stopButton = document.getElementById("stop");
const resetButton = document.getElementById("reset");

function start() {
    if (!isRunning) {
        isRunning = true;
        startTime = Date.now(); 
        timer = setInterval(updateDisplay, 1000);
    }
}

function stop() {
    if (isRunning) { 
        clearInterval(timer);
        isRunning = false;
        if (startTime !== null) {
            elapsedSeconds += Math.floor((Date.now() - startTime) / 1000);
            startTime = null;
        }
        saveDuration();
    }
}


function updateDisplay() {
    const totalSeconds = elapsedSeconds + (isRunning ? Math.floor((Date.now() - startTime) / 1000) : 0);

    hours = Math.floor(totalSeconds / 3600);
    minutes = Math.floor((totalSeconds % 3600) / 60);
    seconds = totalSeconds % 60;

    display.textContent =
        (hours < 10 ? "0" : "") + hours + ":" +
        (minutes < 10 ? "0" : "") + minutes + ":" +
        (seconds < 10 ? "0" : "") + seconds;
}

function reset() {
    clearInterval(timer);
    isRunning = false;
    elapsedSeconds = 0;
    startTime = null; 
    display.textContent = "00:00:00";
}

function saveDuration() {
    const duration = display.textContent;
    fetch('/record_activity', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ duration: duration })
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

startButton.addEventListener("click", start);
stopButton.addEventListener("click", stop);
resetButton.addEventListener("click", reset);
