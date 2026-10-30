const challengeMessage = document.getElementById('challengeMessage');

function showChallengeMessage(text, success = false) {
  if (!challengeMessage) return;
  challengeMessage.textContent = text;
  challengeMessage.style.color = success ? '#15966a' : '#c83c50';
}

document.addEventListener('click', async (event) => {
  const button = event.target.closest('.claim-reward');
  if (!button || button.disabled) return;
  button.disabled = true;
  button.textContent = 'Claiming...';
  try {
    const response = await fetch(`/api/challenges/${button.dataset.challengeId}/claim`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'}
    });
    const data = await response.json();
    if (data.already_claimed) {
      button.textContent = '✓ Reward Claimed';
      showChallengeMessage(data.message, true);
      return;
    }
    if (!response.ok || !data.success) throw new Error(data.message || 'Unable to claim reward. Please try again.');
    button.textContent = '✓ Reward Claimed';
    document.getElementById('challengePoints').textContent = data.total_points;
    showChallengeMessage(`+${data.points} FITX points. ${data.message}`, true);
  } catch (error) {
    button.disabled = false;
    button.textContent = 'Claim reward';
    showChallengeMessage(error.message);
  }
});