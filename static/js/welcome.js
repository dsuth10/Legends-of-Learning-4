// Dark mode toggle logic for Tailwind CSS (using 'dark' class on html element)
function updateDarkModeIcon() {
    const icon = document.getElementById('darkModeIcon');
    if (!icon) return;
    
    const isDark = document.documentElement.classList.contains('dark') || document.body.classList.contains('dark-mode');
    if (isDark) {
        icon.textContent = 'light_mode';
    } else {
        icon.textContent = 'dark_mode';
    }
}

function setDarkMode(enabled) {
    if (enabled) {
        document.documentElement.classList.add('dark');
        document.body.classList.add('dark-mode');
        localStorage.setItem('darkMode', 'true');
    } else {
        document.documentElement.classList.remove('dark');
        document.body.classList.remove('dark-mode');
        localStorage.setItem('darkMode', 'false');
    }
    updateDarkModeIcon();
    document.documentElement.dispatchEvent(new Event('darkmodechange'));
    document.body.dispatchEvent(new Event('darkmodechange'));
}

function toggleDarkMode() {
    const isDark = document.documentElement.classList.contains('dark') || document.body.classList.contains('dark-mode');
    setDarkMode(!isDark);
}

// On page load, set mode from localStorage
window.addEventListener('DOMContentLoaded', function() {
    const darkPref = localStorage.getItem('darkMode');
    if (darkPref === 'true') {
        setDarkMode(true);
    } else {
        if (document.body.classList.contains('dark-mode')) {
            document.documentElement.classList.add('dark');
        }
        updateDarkModeIcon();
    }
    
    // Attach toggle to button if present
    const btn = document.getElementById('darkModeToggle');
    if (btn) {
        btn.addEventListener('click', toggleDarkMode);
    }
});


