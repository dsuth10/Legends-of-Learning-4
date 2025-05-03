// Dark mode toggle logic
function updateDarkModeIcon() {
  const icon = document.getElementById('darkModeIcon');
  if (!icon) return;
  if (document.body.classList.contains('dark-mode')) {
    // Use sun icon for dark mode (to indicate switch to light)
    icon.className = 'bi bi-sun';
    icon.textContent = icon.className ? '' : '☀️';
  } else {
    // Use moon icon for light mode (to indicate switch to dark)
    icon.className = 'bi bi-moon';
    icon.textContent = icon.className ? '' : '🌙';
  }
}

function setDarkMode(enabled) {
  if (enabled) {
    document.body.classList.add('dark-mode');
    localStorage.setItem('darkMode', 'true');
  } else {
    document.body.classList.remove('dark-mode');
    localStorage.setItem('darkMode', 'false');
  }
  updateDarkModeIcon();
  // Accessibility: trigger event
  document.body.dispatchEvent(new Event('darkmodechange'));
}

function toggleDarkMode() {
  setDarkMode(!document.body.classList.contains('dark-mode'));
}

// On page load, set mode from localStorage
window.addEventListener('DOMContentLoaded', function() {
  const darkPref = localStorage.getItem('darkMode');
  if (darkPref === 'true') {
    setDarkMode(true);
  } else {
    updateDarkModeIcon();
  }
  // Attach toggle to button if present
  const btn = document.getElementById('darkModeToggle');
  if (btn) {
    btn.addEventListener('click', toggleDarkMode);
  }
}); 