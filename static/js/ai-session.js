const sessionButton = document.getElementById('sessionButton');
const sessionTimer = document.getElementById('sessionTimer');
const sessionState = document.getElementById('sessionState');
const signalText = document.getElementById('signalText');
const detectedMode = document.getElementById('detectedMode');
const stepCount = document.getElementById('stepCount');
const confidence = document.getElementById('confidence');
const message = document.getElementById('activityMessage');

let startedAt = 0;
let timerId = null;
let steps = 0;
let motionSamples = 0;
let motionTotal = 0;
let lastPeak = 0;
let listening = false;

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60).toString().padStart(2, '0');
  const remainder = (seconds % 60).toString().padStart(2, '0');
  return `${minutes}:${remainder}`;
}

function updateTimer() {
  const elapsed = Math.floor((Date.now() - startedAt) / 1000);
  sessionTimer.textContent = formatTime(elapsed);
  if (elapsed > 4 && !motionSamples) signalText.textContent = 'Session captured from elapsed time';
}

function captureMotion(event) {
  const acceleration = event.accelerationIncludingGravity;
  if (!acceleration) return;
  const magnitude = Math.sqrt(
    (acceleration.x || 0) ** 2 + (acceleration.y || 0) ** 2 + (acceleration.z || 0) ** 2
  );
  const movement = Math.abs(magnitude - 9.8);
  motionSamples += 1;
  motionTotal += Math.min(movement, 4);
  if (movement > 1.7 && Date.now() - lastPeak > 360) {
    steps += 1;
    lastPeak = Date.now();
    stepCount.textContent = steps;
  }
}

async function requestMotionPermission() {
  if (typeof DeviceMotionEvent === 'undefined') return false;
  if (typeof DeviceMotionEvent.requestPermission === 'function') {
    return (await DeviceMotionEvent.requestPermission()) === 'granted';
  }
  return true;
}

async function startSession() {
  message.textContent = '';
  try {
    const permitted = await requestMotionPermission();
    if (permitted) {
      window.addEventListener('devicemotion', captureMotion);
      listening = true;
      signalText.textContent = 'Listening for phone movement';
    } else {
      signalText.textContent = 'Motion access declined; timing still works';
    }
  } catch (_) {
    signalText.textContent = 'Timing session; motion sensor unavailable';
  }
  startedAt = Date.now();
  steps = 0;
  motionSamples = 0;
  motionTotal = 0;
  stepCount.textContent = '0';
  confidence.textContent = '--';
  detectedMode.textContent = 'Capturing';
  sessionState.textContent = 'Live';
  sessionButton.textContent = 'Finish session';
  sessionButton.classList.add('is-live');
  timerId = window.setInterval(updateTimer, 1000);
}

async function finishSession() {
  const durationSeconds = Math.floor((Date.now() - startedAt) / 1000);
  if (durationSeconds < 10) {
    message.textContent = 'Keep moving for at least 10 seconds so FITX can identify the session.';
    message.style.color = '#c83c50';
    return;
  }
  window.clearInterval(timerId);
  if (listening) window.removeEventListener('devicemotion', captureMotion);
  listening = false;
  sessionState.textContent = 'Thinking';
  sessionButton.disabled = true;
  signalText.textContent = 'AI is classifying your movement';

  const minutes = Math.max(durationSeconds / 60, 1);
  const cadence = steps / minutes;
  const movementScore = motionSamples ? Math.min(motionTotal / motionSamples, 1) : 0;
  const response = await fetch('/api/ai-session', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      duration_seconds: durationSeconds,
      steps,
      movement_score: movementScore,
      pace: cadence * 0.04
    })
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'The AI session could not be saved.');

  detectedMode.textContent = data.activity;
  confidence.textContent = `${Math.round(data.confidence * 100)}%`;
  signalText.textContent = data.reason;
  message.textContent = `${data.coach_message} Next reminder: ${data.next_reminder}.`;
  message.style.color = '#126b4b';
  sessionState.textContent = 'Done';
  sessionButton.textContent = 'Start another';
  sessionButton.disabled = false;
  sessionButton.classList.remove('is-live');
  window.localStorage.setItem('fitx-next-reminder', data.next_reminder);
}

sessionButton?.addEventListener('click', () => {
  if (!startedAt || sessionState.textContent === 'Done') {
    startedAt = 0;
    startSession().catch((error) => { message.textContent = error.message; });
  } else {
    finishSession().catch((error) => {
      message.textContent = error.message;
      message.style.color = '#c83c50';
      sessionButton.disabled = false;
      sessionState.textContent = 'Ready';
    });
  }
});
