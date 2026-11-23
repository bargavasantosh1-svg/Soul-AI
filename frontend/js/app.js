// app.js - SOUL chat page (chat + speaking + listening with auto-stop)

const statusLight = document.getElementById("status-light");
const statusText = document.getElementById("status-text");
const messagesBox = document.getElementById("messages");
const errorBox = document.getElementById("error-box");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const voiceBtn = document.getElementById("voice-btn");
const micBtn = document.getElementById("mic-btn");

const GREETING = "Hello Bargav. I am SOUL. How can I help you?";

// ---------- Settings you can change ----------

const MAX_RECORD_SECONDS = 30;   // never record longer than this
const SILENCE_SECONDS = 1.5;     // stop after this much quiet (after you spoke)
const NO_SPEECH_SECONDS = 8;     // give up if you never start talking
const MIN_VOLUME = 0.02;         // quietest level counted as speech (0 to 1)
const NOISE_MULTIPLIER = 3;      // speech must be this many times louder than the room

// ---------- Speaking settings ----------

let voiceOn = true;
try {
  voiceOn = localStorage.getItem("soulVoiceOn") !== "false";
} catch (e) {
  voiceOn = true;
}

let currentAudio = null;
let currentAudioUrl = null;

function updateVoiceButton() {
  voiceBtn.textContent = voiceOn ? "Voice: On" : "Voice: Off";
}

function stopSpeaking() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (currentAudioUrl) {
    URL.revokeObjectURL(currentAudioUrl);
    currentAudioUrl = null;
  }
}

async function speak(text) {
  if (!voiceOn || !text) {
    return;
  }
  stopSpeaking();
  try {
    const response = await fetch("/api/voice/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text }),
    });
    if (!response.ok) {
      showError(await readErrorDetail(response));
      return;
    }
    const blob = await response.blob();
    currentAudioUrl = URL.createObjectURL(blob);
    currentAudio = new Audio(currentAudioUrl);
    await currentAudio.play();
  } catch (e) {
    // The text reply is already on screen, so we stay quiet.
  }
}

voiceBtn.addEventListener("click", function () {
  voiceOn = !voiceOn;
  try {
    localStorage.setItem("soulVoiceOn", String(voiceOn));
  } catch (e) {
    // not saving is fine
  }
  if (!voiceOn) {
    stopSpeaking();
  }
  updateVoiceButton();
});

updateVoiceButton();

// ---------- Small helper functions ----------

function addMessage(who, text) {
  const row = document.createElement("div");
  row.className = "message " + (who === "user" ? "user" : "assistant");
  if (who === "thinking") {
    row.classList.add("thinking");
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  row.appendChild(bubble);
  messagesBox.appendChild(row);
  messagesBox.scrollTop = messagesBox.scrollHeight;
  return row;
}

function showError(text) {
  errorBox.textContent = text;
  errorBox.classList.remove("hidden");
}

function hideError() {
  errorBox.textContent = "";
  errorBox.classList.add("hidden");
}

function setBusy(isBusy) {
  sendBtn.disabled = isBusy;
  messageInput.disabled = isBusy;
  newChatBtn.disabled = isBusy;
  micBtn.disabled = isBusy;
  if (!isBusy) {
    messageInput.focus();
  }
}

async function readErrorDetail(response) {
  try {
    const data = await response.json();
    if (data && typeof data.detail === "string") {
      return data.detail;
    }
  } catch (e) {
    // the reply was not JSON, so fall through
  }
  return "Something went wrong (code " + response.status + ").";
}

// ---------- Status light ----------

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error("bad status");
    }
    const data = await response.json();

    if (data.status === "online" && data.api_key_configured) {
      statusLight.className = "status-light online";
      statusText.textContent = "Online";
    } else if (data.status === "online") {
      statusLight.className = "status-light offline";
      statusText.textContent = "API key missing";
    } else {
      statusLight.className = "status-light offline";
      statusText.textContent = "Offline";
    }
  } catch (e) {
    statusLight.className = "status-light offline";
    statusText.textContent = "Offline";
  }
}

// ---------- Sending a message ----------

async function sendMessage(text) {
  hideError();
  stopSpeaking();
  addMessage("user", text);
  const thinkingRow = addMessage("thinking", "SOUL is thinking...");
  setBusy(true);

  let reply = "";
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    thinkingRow.remove();

    if (!response.ok) {
      showError(await readErrorDetail(response));
    } else {
      const data = await response.json();
      reply = data.reply;
      addMessage("assistant", reply);
    }
  } catch (e) {
    thinkingRow.remove();
    showError("I cannot reach the SOUL server. Is it running?");
    statusLight.className = "status-light offline";
    statusText.textContent = "Offline";
  }

  setBusy(false);

  if (reply) {
    speak(reply);
  }
}

chatForm.addEventListener("submit", function (event) {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (text === "") {
    return;
  }
  messageInput.value = "";
  sendMessage(text);
});

// ---------- Listening (microphone with auto-stop) ----------

let mediaRecorder = null;
let recordedChunks = [];
let micStream = null;
let recordTimer = null;
let isRecording = false;

// Volume watching
let audioContext = null;
let analyser = null;
let volumeTimer = null;
let volumeData = null;

let heardSpeech = false;     // did the person start talking?
let lastSpeechTime = 0;      // when was the last loud moment?
let recordStartTime = 0;
let noiseLevel = 0;          // how loud the room is
let noiseSamples = 0;
let stopReason = "manual";   // "manual", "silence", "nospeech" or "limit"

function stopMicStream() {
  if (micStream) {
    micStream.getTracks().forEach(function (track) {
      track.stop();
    });
    micStream = null;
  }
}

function stopVolumeWatching() {
  if (volumeTimer) {
    clearInterval(volumeTimer);
    volumeTimer = null;
  }
  if (audioContext) {
    audioContext.close().catch(function () {});
    audioContext = null;
  }
  analyser = null;
  volumeData = null;
}

function currentVolume() {
  // Returns a number from 0 (silent) to about 1 (very loud)
  analyser.getByteTimeDomainData(volumeData);
  let sum = 0;
  for (let i = 0; i < volumeData.length; i++) {
    const v = (volumeData[i] - 128) / 128;
    sum += v * v;
  }
  return Math.sqrt(sum / volumeData.length);
}

function startVolumeWatching(stream) {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    audioContext = new Ctx();
    const source = audioContext.createMediaStreamSource(stream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 1024;
    volumeData = new Uint8Array(analyser.fftSize);
    source.connect(analyser);
  } catch (e) {
    // No auto-stop, but manual Stop still works
    analyser = null;
    return;
  }

  heardSpeech = false;
  noiseLevel = 0;
  noiseSamples = 0;
  recordStartTime = Date.now();
  lastSpeechTime = Date.now();

  volumeTimer = setInterval(function () {
    if (!analyser || !isRecording) {
      return;
    }
    const now = Date.now();
    const volume = currentVolume();
    const elapsed = now - recordStartTime;

    // First 0.4 seconds: learn how noisy the room is
    if (elapsed < 400) {
      noiseLevel += volume;
      noiseSamples += 1;
      return;
    }
    const roomNoise = noiseSamples > 0 ? noiseLevel / noiseSamples : 0;
    const threshold = Math.max(MIN_VOLUME, roomNoise * NOISE_MULTIPLIER);

    if (volume > threshold) {
      heardSpeech = true;
      lastSpeechTime = now;
    }

    if (heardSpeech && now - lastSpeechTime > SILENCE_SECONDS * 1000) {
      stopRecording("silence");
    } else if (!heardSpeech && elapsed > NO_SPEECH_SECONDS * 1000) {
      stopRecording("nospeech");
    }
  }, 100);
}

async function startRecording() {
  hideError();
  stopSpeaking(); // SOUL stops talking so it does not hear itself

  if (!navigator.mediaDevices || !window.MediaRecorder) {
    showError("This browser cannot record sound. Please use Chrome or Edge.");
    return;
  }

  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    showError("I need permission to use the microphone. Click the lock icon in the address bar and allow the microphone.");
    return;
  }

  recordedChunks = [];
  stopReason = "manual";
  mediaRecorder = new MediaRecorder(micStream);

  mediaRecorder.addEventListener("dataavailable", function (event) {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data);
    }
  });

  mediaRecorder.addEventListener("stop", function () {
    const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || "audio/webm" });
    const reason = stopReason;
    stopMicStream();
    stopVolumeWatching();
    handleRecording(blob, reason);
  });

  mediaRecorder.start();
  isRecording = true;
  micBtn.classList.add("recording");
  micBtn.textContent = "Stop";
  statusText.textContent = "Listening...";

  startVolumeWatching(micStream);

  // Safety: stop automatically after a time limit
  recordTimer = setTimeout(function () {
    stopRecording("limit");
  }, MAX_RECORD_SECONDS * 1000);
}

function stopRecording(reason) {
  if (recordTimer) {
    clearTimeout(recordTimer);
    recordTimer = null;
  }
  if (mediaRecorder && isRecording) {
    isRecording = false;
    stopReason = reason || "manual";
    micBtn.classList.remove("recording");
    micBtn.textContent = "Mic";
    mediaRecorder.stop();
  }
}

async function handleRecording(blob, reason) {
  // If the person never spoke, do not bother the server
  if (reason === "nospeech") {
    showError("I did not hear anything. Click Mic and try again.");
    checkHealth();
    return;
  }

  if (blob.size < 1000) {
    showError("I did not hear anything. Please try again.");
    checkHealth();
    return;
  }

  statusText.textContent = "Understanding...";
  setBusy(true);

  let heard = "";
  try {
    const form = new FormData();
    form.append("audio", blob, "recording.webm");
    const response = await fetch("/api/voice/listen", {
      method: "POST",
      body: form,
    });
    if (!response.ok) {
      showError(await readErrorDetail(response));
    } else {
      const data = await response.json();
      heard = (data.text || "").trim();
    }
  } catch (e) {
    showError("I cannot reach the SOUL server. Is it running?");
  }

  setBusy(false);
  checkHealth();

  if (heard === "") {
    if (errorBox.classList.contains("hidden")) {
      showError("I did not catch any words. Please try again.");
    }
    return;
  }

  sendMessage(heard);
}

micBtn.addEventListener("click", function () {
  if (isRecording) {
    stopRecording("manual");
  } else {
    startRecording();
  }
});

// ---------- New chat ----------

newChatBtn.addEventListener("click", async function () {
  hideError();
  stopSpeaking();
  setBusy(true);
  try {
    const response = await fetch("/api/reset", { method: "POST" });
    if (!response.ok) {
      showError(await readErrorDetail(response));
    } else {
      messagesBox.innerHTML = "";
      addMessage("assistant", GREETING);
    }
  } catch (e) {
    showError("I cannot reach the SOUL server. Is it running?");
  }
  setBusy(false);
});

// ---------- When the page opens ----------

checkHealth();
setInterval(checkHealth, 15000);