const game = document.getElementById('runnerGame');
const player = document.getElementById('runnerPlayer');
const overlay = document.getElementById('gameOverlay');
const countdown = document.getElementById('countdown');
const startButton = document.getElementById('startGame');
const pauseButton = document.getElementById('pauseGame');
const finishButton = document.getElementById('finishGame');
const completion = document.getElementById('completionPanel');
const playAgain = document.getElementById('playAgain');
let lane = 1;
let score = 0;
let coins = 0;
let distance = 0;
let energy = 3;
let startedAt = 0;
let gameTimer = null;
let running = false;
let paused = false;

function showToast(text) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = text;
  toast.classList.add('show');
  window.setTimeout(() => toast.classList.remove('show'), 2400);
}

function updateLane() {
  const positions = ['28%', 'calc(50% - 28px)', 'calc(72% - 57px)'];
  player.style.left = positions[lane];
}

function updateHud() {
  document.getElementById('gameScore').textContent = score;
  document.getElementById('gameCoins').textContent = coins;
  document.getElementById('gameDistance').textContent = distance;
  document.getElementById('gameEnergy').textContent = '♥'.repeat(energy) + '♡'.repeat(3 - energy);
}

function move(direction) {
  if (!running || paused) return;
  lane = Math.max(0, Math.min(2, lane + direction));
  updateLane();
  score += 5;
  distance += 7;
  if (Math.random() > .74) { coins += 1; showToast('+1 coin collected'); }
  updateHud();
}

function resetGame() {
  window.clearInterval(gameTimer);
  lane = 1; score = 0; coins = 0; distance = 0; energy = 3; paused = false; running = false;
  updateLane(); updateHud();
  countdown.textContent = 'READY?';
  overlay.hidden = false;
  completion.hidden = true;
  startButton.textContent = 'Start game';
  startButton.disabled = false;
  startButton.hidden = false;
  startButton.setAttribute('aria-label', 'Start game');
  game.dataset.state = 'ready';
}

function startGame() {
  if (running) return;
  running = true;
  startedAt = Date.now();
  startButton.textContent = 'Game active';
  startButton.disabled = true;
  startButton.setAttribute('aria-label', 'Game active');
  game.dataset.state = 'active';
  let count = 3;
  overlay.hidden = true;
  countdown.textContent = count;
  const interval = window.setInterval(() => {
    count -= 1;
    countdown.textContent = count > 0 ? count : 'GO!';
    if (count <= 0) {
      window.clearInterval(interval);
      window.setTimeout(() => { countdown.textContent = ''; }, 500);
    }
  }, 650);
  gameTimer = window.setInterval(() => {
    if (running && !paused) { distance += 4; score += 2; updateHud(); }
  }, 1000);
}

async function finishGame() {
  running = false;
  window.clearInterval(gameTimer);
  const response = await fetch('/api/game-session', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({score, distance, duration_minutes: Math.max(1, Math.round((Date.now() - startedAt) / 60000))}) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to save run.');
  document.getElementById('finalScore').textContent = data.score;
  document.getElementById('finalXp').textContent = `+${data.xp}`;
  document.getElementById('finalCoins').textContent = `+${data.coins}`;
  completion.hidden = false;
  startButton.textContent = 'Game over';
  game.dataset.state = 'complete';
  showToast(`+${data.xp} XP earned!`);
}

function handleKey(event) {
  if (event.key === 'ArrowLeft' || event.key.toLowerCase() === 'a') move(-1);
  if (event.key === 'ArrowRight' || event.key.toLowerCase() === 'd') move(1);
  if (event.key === ' ' && running) { paused = !paused; pauseButton.textContent = paused ? 'Resume' : 'Pause'; countdown.textContent = paused ? 'PAUSED' : ''; }
}

startButton?.addEventListener('click', startGame);
pauseButton?.addEventListener('click', () => { if (!running) return; paused = !paused; pauseButton.textContent = paused ? 'Resume' : 'Pause'; countdown.textContent = paused ? 'PAUSED' : ''; });
playAgain?.addEventListener('click', () => { resetGame(); startGame(); });
finishButton?.addEventListener('click', () => { if (running) finishGame().catch((error) => showToast(error.message)); });
document.addEventListener('keydown', handleKey);
game?.addEventListener('click', (event) => { if (!running || event.target.closest('button')) return; move(event.clientX < window.innerWidth / 2 ? -1 : 1); });
window.setInterval(() => { if (running && !paused && distance > 0 && distance % 170 === 0) { energy = Math.max(0, energy - 1); updateHud(); if (!energy) finishGame().catch(() => {}); } }, 1000);
updateLane(); updateHud();
