/**
 * Boot modular tools on the fullscreen classroom display.
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const cfgEl = document.getElementById('classroom-tools-config');
    const idsEl = document.getElementById('classroom-tool-ids');
    const grid = document.getElementById('tool-grid');
    if (!cfgEl || !idsEl || !grid || !window.ToolRegistry) return;

    let config;
    try {
      config = JSON.parse(cfgEl.textContent || 'null');
    } catch (e) {
      console.error('Invalid classroom tools config JSON', e);
      return;
    }
    if (!config) return;

    let toolIds;
    try {
      toolIds = JSON.parse(idsEl.textContent || '[]');
    } catch (e) {
      console.error('Invalid tool ids JSON', e);
      return;
    }

    grid.classList.toggle('tool-grid--dual', toolIds.length > 1);

    toolIds.forEach(function (name) {
      const slot = document.createElement('div');
      slot.className = 'tool-slot';
      slot.dataset.tool = name;
      grid.appendChild(slot);

      const toolConfig = buildToolConfig(name, config);
      try {
        const instance = ToolRegistry.create(name, toolConfig, slot);
        slot._toolInstance = instance;
      } catch (err) {
        slot.innerHTML =
          '<div class="alert alert-warning m-3">Tool <code>' +
          name +
          '</code> is not available: ' +
          err.message +
          '</div>';
      }
    });

    const fsBtn = document.getElementById('display-toggle-fullscreen');
    if (fsBtn) {
      fsBtn.addEventListener('click', function () {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(function () {});
        } else {
          document.exitFullscreen();
        }
      });
    }
  });

  function buildToolConfig(name, cfg) {
    if (name === 'volume_meter') {
      const urls = cfg.csrf_protected_urls || {};
      return Object.assign({}, cfg.volume_meter || {}, {
        classId: cfg.class_id,
        penaltyUrl: urls.penalty,
        rewardUrl: urls.reward,
      });
    }
    return cfg;
  }
})();
