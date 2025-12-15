// Dark mode toggle logic for Tailwind CSS (using 'dark' class on html element)
function updateDarkModeIcon() {
    const icon = document.getElementById('darkModeIcon');
    if (!icon) return;
    
    if (document.documentElement.classList.contains('dark')) {
        // Use light_mode icon when in dark mode (to indicate switch to light)
        icon.textContent = 'light_mode';
    } else {
        // Use dark_mode icon when in light mode (to indicate switch to dark)
        icon.textContent = 'dark_mode';
    }
}

function setDarkMode(enabled) {
    if (enabled) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('darkMode', 'true');
    } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('darkMode', 'false');
    }
    updateDarkModeIcon();
    // Accessibility: trigger event
    document.documentElement.dispatchEvent(new Event('darkmodechange'));
}

function toggleDarkMode() {
    const isDark = document.documentElement.classList.contains('dark');
    setDarkMode(!isDark);
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

