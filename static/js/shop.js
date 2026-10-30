document.querySelectorAll('.shop-btn').forEach((button) => {
  button.addEventListener('click', () => {
    if (button.disabled) return;
    button.disabled = true;
    button.textContent = 'UNLOCKED';
    const toast = document.getElementById('toast');
    if (toast) {
      toast.textContent = 'Reward unlocked for your player!';
      toast.classList.add('show');
      window.setTimeout(() => toast.classList.remove('show'), 2200);
    }
  });
});
