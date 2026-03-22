/**
 * Classroom tools setup page: load/save volume meter config, launch display URL.
 */
(function () {
  'use strict';

  const select = document.getElementById('ct-class-select');
  const statusEl = document.getElementById('ct-save-status');
  const launch = document.getElementById('ct-launch-display');

  if (!select || !window.classroomToolsApiBase) return;

  const fields = {
    threshold: document.getElementById('ct-threshold'),
    breach_duration_seconds: document.getElementById('ct-breach-seconds'),
    breach_cooldown_seconds: document.getElementById('ct-cooldown'),
    damage_amount: document.getElementById('ct-damage'),
    timer_minutes: document.getElementById('ct-timer-min'),
    base_xp_reward: document.getElementById('ct-base-xp'),
    base_gold_reward: document.getElementById('ct-base-gold'),
  };

  const thresholdLabel = document.getElementById('ct-threshold-label');
  const previewFill = document.getElementById('ct-preview-fill');
  const previewLine = document.getElementById('ct-preview-line');

  function apiUrl(classId) {
    return window.classroomToolsApiBase + '/' + classId;
  }

  function thresholdAsFraction() {
    const v = parseInt(fields.threshold.value, 10);
    return Math.max(0.05, Math.min(0.95, v / 100));
  }

  function updateThresholdUi() {
    const t = thresholdAsFraction();
    if (thresholdLabel) {
      thresholdLabel.textContent = '(' + Math.round(t * 100) + '%)';
    }
    if (previewLine) {
      previewLine.style.bottom = t * 100 + '%';
    }
    if (previewFill) {
      previewFill.style.height = Math.min(t * 100 * 0.85, 85) + '%';
    }
  }

  function readFormConfig() {
    return {
      threshold: thresholdAsFraction(),
      breach_duration_seconds: parseInt(fields.breach_duration_seconds.value, 10) || 5,
      breach_cooldown_seconds: parseInt(fields.breach_cooldown_seconds.value, 10) || 0,
      damage_amount: parseInt(fields.damage_amount.value, 10) || 10,
      timer_minutes: parseInt(fields.timer_minutes.value, 10) || 15,
      base_xp_reward: parseInt(fields.base_xp_reward.value, 10) || 0,
      base_gold_reward: parseInt(fields.base_gold_reward.value, 10) || 0,
    };
  }

  function applyConfig(cfg) {
    if (!cfg) return;
    const pct = Math.round((cfg.threshold != null ? cfg.threshold : 0.35) * 100);
    fields.threshold.value = String(Math.max(5, Math.min(95, pct)));
    fields.breach_duration_seconds.value = String(cfg.breach_duration_seconds ?? 5);
    fields.breach_cooldown_seconds.value = String(cfg.breach_cooldown_seconds ?? 2);
    fields.damage_amount.value = String(cfg.damage_amount ?? 10);
    fields.timer_minutes.value = String(cfg.timer_minutes ?? 15);
    fields.base_xp_reward.value = String(cfg.base_xp_reward ?? 50);
    fields.base_gold_reward.value = String(cfg.base_gold_reward ?? 25);
    updateThresholdUi();
  }

  async function loadConfig() {
    const classId = select.value;
    statusEl.textContent = 'Loading…';
    try {
      const res = await fetch(apiUrl(classId), { credentials: 'same-origin' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Load failed');
      applyConfig(data.config);
      statusEl.textContent = '';
    } catch (e) {
      statusEl.textContent = 'Could not load config: ' + e.message;
    }
  }

  function updateLaunchLink() {
    const classId = select.value;
    const base = window.location.origin;
    const path = '/teacher/classroom-tools/display?class_id=' + encodeURIComponent(classId) + '&tools=volume_meter';
    launch.href = base + path;
  }

  document.getElementById('ct-save-config').addEventListener('click', async function () {
    const classId = select.value;
    statusEl.textContent = 'Saving…';
    try {
      const res = await fetch(apiUrl(classId), {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: readFormConfig() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Save failed');
      applyConfig(data.config);
      statusEl.textContent = 'Saved.';
    } catch (e) {
      statusEl.textContent = 'Save failed: ' + e.message;
    }
  });

  fields.threshold.addEventListener('input', updateThresholdUi);

  select.addEventListener('change', function () {
    loadConfig();
    updateLaunchLink();
  });

  updateThresholdUi();
  loadConfig();
  updateLaunchLink();
})();
