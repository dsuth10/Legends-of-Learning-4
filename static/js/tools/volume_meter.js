/**
 * Volume meter: microphone RMS, sustained threshold breach -> penalty API, timer -> reward API.
 */
(function (global) {
  'use strict';

  function clamp(n, a, b) {
    return Math.max(a, Math.min(b, n));
  }

  function formatTime(ms) {
    if (ms < 0) ms = 0;
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const r = s % 60;
    return m + ':' + (r < 10 ? '0' : '') + r;
  }

  class VolumeMeter {
    constructor(config, container) {
      this.config = config || {};
      this.container = container;
      this.classId = config.classId;
      this.penaltyUrl = config.penaltyUrl;
      this.rewardUrl = config.rewardUrl;

      this.threshold = typeof config.threshold === 'number' ? config.threshold : 0.35;
      this.breachDurationMs = (config.breach_duration_seconds || 5) * 1000;
      this.cooldownMs = (config.breach_cooldown_seconds || 2) * 1000;
      this.damageAmount = config.damage_amount || 10;
      this.timerMinutes = config.timer_minutes || 15;
      this.baseXp = config.base_xp_reward || 0;
      this.baseGold = config.base_gold_reward || 0;

      this.rewardMultiplier = 1;
      this.breachCount = 0;
      this.sessionRemainingMs = 0;
      this.sessionRunning = false;
      this.paused = false;
      this.completed = false;

      this._raf = null;
      this._audioCtx = null;
      this._analyser = null;
      this._stream = null;
      this._breachStart = null;
      this._cooldownUntil = 0;
      this._lastFrame = 0;
      this._volumeEma = 0;

      this._buildUi();
    }

    _buildUi() {
      const el = document.createElement('div');
      el.className = 'volume-meter-widget';
      el.innerHTML =
        '<div class="vm-header d-flex justify-content-between align-items-center flex-wrap gap-2">' +
        '  <h2 class="h3 mb-0"><i class="fas fa-volume-high me-2"></i>Volume</h2>' +
        '  <div class="vm-controls btn-group" role="group">' +
        '    <button type="button" class="btn btn-success btn-lg vm-start">Start</button>' +
        '    <button type="button" class="btn btn-warning btn-lg vm-pause" disabled>Pause</button>' +
        '    <button type="button" class="btn btn-outline-light btn-lg vm-reset">Reset</button>' +
        '  </div>' +
        '</div>' +
        '<p class="vm-mic-hint text-white-50 small mb-3">Allow microphone access when prompted. Processing stays in this browser.</p>' +
        '<div class="row g-4 align-items-stretch">' +
        '  <div class="col-lg-5">' +
        '    <div class="vm-meter-wrap">' +
        '      <div class="vm-meter" aria-label="Noise level">' +
        '        <div class="vm-meter-fill"></div>' +
        '        <div class="vm-meter-threshold"></div>' +
        '      </div>' +
        '      <div class="vm-level-readout small text-white-50 mt-2">Level: <span class="vm-level-pct">0</span>%</div>' +
        '    </div>' +
        '  </div>' +
        '  <div class="col-lg-7">' +
        '    <div class="vm-stat-card">' +
        '      <div class="vm-timer-display" aria-live="polite">' +
        '        <span class="vm-timer-label">Session</span>' +
        '        <span class="vm-timer-value">—</span>' +
        '      </div>' +
        '      <div class="vm-reward-display mt-3">' +
        '        <div class="text-white-50 small">Potential reward (per character)</div>' +
        '        <div class="vm-reward-xp h5 mb-1"><span class="vm-xp-val">0</span> XP</div>' +
        '        <div class="vm-reward-gold h5 mb-1"><span class="vm-gold-val">0</span> Gold</div>' +
        '        <div class="vm-multiplier small text-warning">Multiplier: 100%</div>' +
        '      </div>' +
        '      <div class="vm-breach-display mt-3 small">Noise breaches: <strong class="vm-breach-count">0</strong></div>' +
        '      <div class="vm-status-msg mt-2 small text-info" role="status"></div>' +
        '    </div>' +
        '  </div>' +
        '</div>';

      this.container.appendChild(el);
      this.root = el;
      this.elMeterFill = el.querySelector('.vm-meter-fill');
      this.elThreshold = el.querySelector('.vm-meter-threshold');
      this.elLevelPct = el.querySelector('.vm-level-pct');
      this.elTimer = el.querySelector('.vm-timer-value');
      this.elXp = el.querySelector('.vm-xp-val');
      this.elGold = el.querySelector('.vm-gold-val');
      this.elMult = el.querySelector('.vm-multiplier');
      this.elBreaches = el.querySelector('.vm-breach-count');
      this.elStatus = el.querySelector('.vm-status-msg');
      this.btnStart = el.querySelector('.vm-start');
      this.btnPause = el.querySelector('.vm-pause');
      this.btnReset = el.querySelector('.vm-reset');

      this.elThreshold.style.bottom = this.threshold * 100 + '%';

      this.btnStart.addEventListener('click', () => this.start());
      this.btnPause.addEventListener('click', () => this.togglePause());
      this.btnReset.addEventListener('click', () => this.resetSession());

      this._updateRewardDisplay();
      this._setStatus('Ready. Press Start to begin.');
    }

    _setStatus(msg) {
      if (this.elStatus) this.elStatus.textContent = msg || '';
    }

    _updateRewardDisplay() {
      const xp = Math.floor(this.baseXp * this.rewardMultiplier);
      const gold = Math.floor(this.baseGold * this.rewardMultiplier);
      this.elXp.textContent = String(xp);
      this.elGold.textContent = String(gold);
      this.elMult.textContent =
        'Multiplier: ' + Math.round(this.rewardMultiplier * 100) + '% (halves each breach)';
    }

    async start() {
      if (this.completed) {
        this._setStatus('Press Reset to start a new session.');
        return;
      }
      if (!this.classId || !this.penaltyUrl || !this.rewardUrl) {
        this._setStatus('Missing class or API URLs.');
        return;
      }
      try {
        this._stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      } catch (e) {
        this._setStatus('Microphone access denied or unavailable.');
        console.error(e);
        return;
      }

      this._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = this._audioCtx.createMediaStreamSource(this._stream);
      this._analyser = this._audioCtx.createAnalyser();
      this._analyser.fftSize = 2048;
      this._analyser.smoothingTimeConstant = 0.85;
      source.connect(this._analyser);

      if (!this.sessionRunning) {
        this.sessionRemainingMs = this.timerMinutes * 60 * 1000;
        this.sessionRunning = true;
      }
      this.paused = false;
      this.btnStart.disabled = true;
      this.btnPause.disabled = false;
      this._breachStart = null;
      this._lastFrame = performance.now();
      this._setStatus('Listening…');

      this._loop = this._loop.bind(this);
      this._raf = requestAnimationFrame(this._loop);
    }

    togglePause() {
      if (!this.sessionRunning || this.completed) return;
      this.paused = !this.paused;
      if (this.paused) {
        this.btnPause.textContent = 'Resume';
        this._breachStart = null;
        if (this._raf) {
          cancelAnimationFrame(this._raf);
          this._raf = null;
        }
        this._setStatus('Paused');
      } else {
        this.btnPause.textContent = 'Pause';
        this._lastFrame = performance.now();
        this._setStatus('Listening…');
        this._raf = requestAnimationFrame(this._loop);
      }
    }

    stopAudio() {
      if (this._raf) {
        cancelAnimationFrame(this._raf);
        this._raf = null;
      }
      if (this._stream) {
        this._stream.getTracks().forEach(function (t) {
          t.stop();
        });
        this._stream = null;
      }
      if (this._audioCtx) {
        this._audioCtx.close().catch(function () {});
        this._audioCtx = null;
      }
      this._analyser = null;
    }

    resetSession() {
      this.stopAudio();
      this.rewardMultiplier = 1;
      this.breachCount = 0;
      this.sessionRunning = false;
      this.paused = false;
      this.completed = false;
      this.sessionRemainingMs = 0;
      this._breachStart = null;
      this._cooldownUntil = 0;
      this._volumeEma = 0;
      this.btnStart.disabled = false;
      this.btnPause.disabled = true;
      this.btnPause.textContent = 'Pause';
      this.elTimer.textContent = '—';
      this.elMeterFill.style.height = '0%';
      this.elLevelPct.textContent = '0';
      this.elBreaches.textContent = '0';
      this.root.classList.remove('vm-flash-penalty', 'vm-flash-reward');
      this._updateRewardDisplay();
      this._setStatus('Ready. Press Start to begin.');
    }

    async _completeSession() {
      if (this.completed) return;
      this.completed = true;
      this.sessionRunning = false;
      this.stopAudio();
      this.btnStart.disabled = true;
      this.btnPause.disabled = true;

      const xp = Math.floor(this.baseXp * this.rewardMultiplier);
      const gold = Math.floor(this.baseGold * this.rewardMultiplier);

      try {
        const res = await fetch(this.rewardUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            class_id: this.classId,
            xp_amount: xp,
            gold_amount: gold,
            reward_multiplier: this.rewardMultiplier,
          }),
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (!res.ok) {
          throw new Error(data.error || 'Reward request failed');
        }
        this._setStatus('Session complete. Rewarded ' + data.rewarded_count + ' character(s).');
      } catch (e) {
        this._setStatus('Timer ended but reward failed: ' + e.message);
        console.error(e);
      }

      this.root.classList.add('vm-flash-reward');
      setTimeout(() => this.root.classList.remove('vm-flash-reward'), 2000);
    }

    async _firePenalty() {
      const self = this;
      try {
        const res = await fetch(this.penaltyUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            class_id: this.classId,
            damage_amount: this.damageAmount,
          }),
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (!res.ok) {
          throw new Error(data.error || 'Penalty request failed');
        }
        self._setStatus('Penalty applied to ' + data.affected_count + ' character(s).');
      } catch (e) {
        self._setStatus('Penalty failed: ' + e.message);
        console.error(e);
      }

      this.rewardMultiplier *= 0.5;
      this.breachCount += 1;
      this.elBreaches.textContent = String(this.breachCount);
      this._updateRewardDisplay();
      this._cooldownUntil = performance.now() + this.cooldownMs;
      this._breachStart = null;
      this.root.classList.add('vm-flash-penalty');
      setTimeout(function () {
        self.root.classList.remove('vm-flash-penalty');
      }, 600);
    }

    _computeRms() {
      if (!this._analyser) return 0;
      const buf = new Uint8Array(this._analyser.fftSize);
      this._analyser.getByteTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128;
        sum += v * v;
      }
      return Math.sqrt(sum / buf.length);
    }

    _loop(now) {
      if (!this.sessionRunning || this.completed || this.paused) return;

      const dt = this._lastFrame ? now - this._lastFrame : 0;
      this._lastFrame = now;

      const rms = this._computeRms();
      const sensitivity = 3.2;
      const instant = clamp(rms * sensitivity, 0, 1);
      this._volumeEma = this._volumeEma * 0.82 + instant * 0.18;
      const level = this._volumeEma;

      const pct = Math.round(level * 100);
      this.elMeterFill.style.height = pct + '%';
      this.elLevelPct.textContent = String(pct);

      this.sessionRemainingMs -= dt;
      this.elTimer.textContent = formatTime(this.sessionRemainingMs);
      if (this.sessionRemainingMs <= 0) {
        this.elTimer.textContent = '0:00';
        this._completeSession();
        return;
      }

      const nowCool = performance.now();
      if (nowCool < this._cooldownUntil) {
        this._breachStart = null;
        this._raf = requestAnimationFrame(this._loop);
        return;
      }

      if (level > this.threshold) {
        if (this._breachStart == null) {
          this._breachStart = now;
        } else if (now - this._breachStart >= this.breachDurationMs) {
          this._firePenalty();
        }
      } else {
        this._breachStart = null;
      }

      this._raf = requestAnimationFrame(this._loop);
    }

    stop() {
      this.paused = true;
      if (this._raf) {
        cancelAnimationFrame(this._raf);
        this._raf = null;
      }
    }

    destroy() {
      this.stopAudio();
      if (this.root && this.root.parentNode) {
        this.root.parentNode.removeChild(this.root);
      }
    }
  }

  if (global.ToolRegistry) {
    global.ToolRegistry.register('volume_meter', VolumeMeter);
  }

  global.VolumeMeter = VolumeMeter;
})(typeof window !== 'undefined' ? window : globalThis);
