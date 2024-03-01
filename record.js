document.addEventListener('DOMContentLoaded', function() {
let recordButton = document.getElementById('recordButton');
let pauseButton = document.getElementById('pauseButton');
let stopButton = document.getElementById('stopButton');
let mediaRecorder;
let audioChunks = [];

recordButton.addEventListener('click', function() {
navigator.mediaDevices.getUserMedia({ audio: true })
.then(stream => {
mediaRecorder = new MediaRecorder(stream);
mediaRecorder.ondataavailable = event => {
audioChunks.push(event.data);
};

mediaRecorder.start();
recordButton.style.display = 'none';
pauseButton.style.display = 'inline';
stopButton.style.display = 'inline';

// Inside the mediaRecorder.onstop event handler
mediaRecorder.onstop = () => {
const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
const formData = new FormData();
formData.append('audioFile', audioBlob);

fetch('/upload', {
method: 'POST',
body: formData,
})
.then(response => response.json())
.then(data => {
document.getElementById('transcript').textContent = data.transcript;
document.getElementById('summary').textContent = data.summary;
console.log('Transcript:', data.transcript);
console.log('Summary:', data.summary);
})
.catch(error => console.error('Error:', error));

// Clear the audioChunks array for the next recording
audioChunks = [];
};

})
.catch(error => console.error('getUserMedia error:', error));
});

pauseButton.addEventListener('click', function() {
if (mediaRecorder.state === 'recording') {
mediaRecorder.pause();
pauseButton.textContent = 'Resume';
} else if (mediaRecorder.state === 'paused') {
mediaRecorder.resume();
pauseButton.textContent = 'Pause';
}
});

stopButton.addEventListener('click', function() {
mediaRecorder.stop();
recordButton.style.display = 'inline';
pauseButton.style.display = 'none';
stopButton.style.display = 'none';
});
});
