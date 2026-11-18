// PavePulse Interactive Utilities & Lively Effects

document.addEventListener('DOMContentLoaded', () => {
  // 1. Auto-dismiss alerts after 6 seconds
  const alerts = document.querySelectorAll('.alert');
  if (alerts.length > 0) {
    setTimeout(() => {
      alerts.forEach(alert => {
        alert.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(() => alert.remove(), 600);
      });
    }, 6000);
  }

  // 2. Animated Number Counters on Homepage
  const counters = document.querySelectorAll('.stat-value[data-target]');
  counters.forEach(counter => {
    const target = +counter.getAttribute('data-target');
    const duration = 1200; // milliseconds
    const frameRate = 30;
    const totalFrames = Math.round(duration / (1000 / frameRate));
    let frame = 0;

    const countUp = () => {
      frame++;
      const progress = frame / totalFrames;
      // easeOutExpo
      const current = Math.round(target * (progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)));
      counter.innerText = current;

      if (frame < totalFrames) {
        requestAnimationFrame(countUp);
      } else {
        counter.innerText = target;
      }
    };

    countUp();
  });

  // 3. Instant Live Table Filter (if table-search input exists)
  const searchInput = document.getElementById('tableSearch');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const term = e.target.value.toLowerCase();
      const rows = document.querySelectorAll('tbody tr');
      rows.forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(term) ? '' : 'none';
      });
    });
  }
});
