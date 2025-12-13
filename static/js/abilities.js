// Ability usage visual feedback and animations

/**
 * Show animated feedback for ability usage
 */
function showAbilityFeedback(data, abilityName, targetName) {
  const feedback = document.getElementById('ability-feedback');
  if (!feedback) return;

  const effectType = data.effect?.type || 'utility';
  const amount = data.effect?.amount || 0;
  const isSuccess = data.success;

  // Determine feedback color and icon based on effect type
  let alertClass = 'alert-info';
  let icon = '✨';
  let animationClass = 'fade-in';

  if (!isSuccess) {
    alertClass = 'alert-danger';
    icon = '❌';
  } else {
    switch(effectType) {
      case 'heal':
        alertClass = 'alert-success';
        icon = '💚';
        animationClass = 'pulse-green';
        break;
      case 'attack':
        alertClass = 'alert-danger';
        icon = '⚔️';
        animationClass = 'shake-red';
        break;
      case 'buff':
        alertClass = 'alert-info';
        icon = '⬆️';
        animationClass = 'glow-blue';
        break;
      case 'debuff':
        alertClass = 'alert-warning';
        icon = '⬇️';
        animationClass = 'glow-orange';
        break;
      case 'defense':
      case 'protect':
        alertClass = 'alert-primary';
        icon = '🛡️';
        animationClass = 'glow-blue';
        break;
      default:
        alertClass = 'alert-info';
        icon = '✨';
    }
  }

  // Create feedback message
  const message = data.message || 'Ability used';
  const xpText = data.xp_awarded > 0 ? ` <small>(+${data.xp_awarded} XP)</small>` : '';
  
  feedback.innerHTML = `
    <div class="alert ${alertClass} ability-feedback-message ${animationClass}" role="alert">
      <strong>${icon} ${message}</strong>${xpText}
    </div>
  `;

  // Auto-hide after 3 seconds
  setTimeout(() => {
    const msg = feedback.querySelector('.ability-feedback-message');
    if (msg) {
      msg.classList.add('fade-out');
      setTimeout(() => {
        if (msg.parentNode) {
          msg.remove();
        }
      }, 500);
    }
  }, 3000);
}

/**
 * Update character stats display without page reload
 */
function updateCharacterStats(characterData, targetData, effect) {
  if (!characterData || !targetData) return;

  // Update health display if target is the main character
  const healthRow = document.querySelector('tr:has(th:contains("Health"))');
  if (healthRow && effect) {
    const healthCell = healthRow.querySelector('td');
    if (healthCell) {
      const currentHealth = targetData.health || characterData.health;
      const maxHealth = targetData.max_health || characterData.max_health;
      
      // Animate health change
      if (effect.type === 'heal' || effect.type === 'attack') {
        animateStatChange(healthCell, effect.amount, effect.type === 'heal' ? 'positive' : 'negative');
      }
      
      // Update health text
      setTimeout(() => {
        healthCell.innerHTML = `${currentHealth} <span class="text-muted small">(Base: ${targetData.health || characterData.health})</span>`;
      }, 500);
    }
  }

  // Update strength/defense if buff/debuff
  if (effect && (effect.type === 'buff' || effect.type === 'debuff' || effect.type === 'protect')) {
    const statName = effect.type === 'protect' ? 'defense' : 'strength';
    const statRow = document.querySelector(`tr:has(th:contains("${statName.charAt(0).toUpperCase() + statName.slice(1)}"))`);
    if (statRow) {
      const statCell = statRow.querySelector('td');
      if (statCell) {
        animateStatChange(statCell, effect.amount, effect.type === 'debuff' ? 'negative' : 'positive');
      }
    }
  }
}

/**
 * Animate stat change with visual indicator
 */
function animateStatChange(element, amount, direction) {
  if (!element || amount === 0) return;

  const isPositive = direction === 'positive';
  const sign = isPositive ? '+' : '';
  const color = isPositive ? '#28a745' : '#dc3545';
  
  // Create floating number indicator
  const indicator = document.createElement('span');
  indicator.className = 'stat-change-indicator';
  indicator.textContent = `${sign}${amount}`;
  indicator.style.cssText = `
    position: absolute;
    color: ${color};
    font-weight: bold;
    font-size: 1.2em;
    pointer-events: none;
    z-index: 1000;
    animation: floatUp 1.5s ease-out forwards;
  `;

  // Position relative to element
  const rect = element.getBoundingClientRect();
  indicator.style.left = `${rect.right - 50}px`;
  indicator.style.top = `${rect.top}px`;

  document.body.appendChild(indicator);

  // Remove after animation
  setTimeout(() => {
    if (indicator.parentNode) {
      indicator.remove();
    }
  }, 1500);

  // Flash the element
  element.style.transition = 'background-color 0.3s';
  element.style.backgroundColor = isPositive ? 'rgba(40, 167, 69, 0.2)' : 'rgba(220, 53, 69, 0.2)';
  setTimeout(() => {
    element.style.backgroundColor = '';
  }, 500);
}

/**
 * Update ability cooldown timer without page reload
 */
function updateAbilityCooldown(abilityId, cooldown) {
  const btn = document.querySelector(`.use-ability-btn[data-ability-id="${abilityId}"]`);
  if (!btn) return;

  if (cooldown > 0) {
    btn.disabled = true;
    const timerSpan = btn.querySelector('.cooldown-timer');
    if (timerSpan) {
      timerSpan.textContent = cooldown;
      btn.innerHTML = `Cooldown: <span class="cooldown-timer">${cooldown}</span>s`;
    } else {
      btn.innerHTML = `Cooldown: <span class="cooldown-timer">${cooldown}</span>s`;
    }
    btn.setAttribute('data-cooldown', cooldown);
  } else {
    btn.disabled = false;
    btn.innerHTML = 'Use';
    btn.setAttribute('data-cooldown', '0');
  }
}

/**
 * Show status effect indicator
 */
function showStatusEffectIndicator(effectType, statAffected, amount, duration) {
  // This will be called when status effects are displayed
  // Implementation depends on where status effects are shown
}








