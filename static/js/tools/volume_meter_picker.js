/**
 * Participant picker for a volume-meter quiet-time session.
 */
(function (global) {
  'use strict';

  function VolumeMeterPicker(root, options) {
    this.root = root;
    this.targetsUrl = options.targetsUrl;
    this._ready = false;
    this._data = null;
  }

  VolumeMeterPicker.prototype.load = async function () {
    const res = await fetch(this.targetsUrl, { credentials: 'same-origin' });
    const body = await res.json().catch(function () {
      return {};
    });
    if (!res.ok || !body.success) {
      throw new Error((body && body.error) || 'Could not load class roster');
    }
    this._data = body.data;
    this._render();
    this._ready = true;
    return this._data;
  };

  VolumeMeterPicker.prototype._render = function () {
    const data = this._data || { clans: [], students: [] };
    const clans = data.clans || [];
    const students = data.students || [];
    let html =
      '<fieldset class="vm-picker">' +
      '<legend class="vm-picker-legend">Participants for this session</legend>' +
      '<label class="vm-picker-option">' +
      '<input type="radio" name="vm-target" value="class" checked> Whole class' +
      ' <span class="vm-picker-meta">(' +
      ((data.classroom && data.classroom.active_character_count) || 0) +
      ' characters)</span></label>' +
      '<label class="vm-picker-option">' +
      '<input type="radio" name="vm-target" value="custom"> Selected clans and students</label>' +
      '<div class="vm-picker-custom" hidden>';
    if (clans.length) {
      html += '<div class="vm-picker-group"><div class="vm-picker-heading">Clans</div>';
      clans.forEach(function (clan) {
        html +=
          '<label class="vm-picker-option"><input type="checkbox" data-clan-id="' +
          clan.id +
          '"> ' +
          escapeHtml(clan.name) +
          ' <span class="vm-picker-meta">(' +
          clan.member_count +
          ')</span></label>';
      });
      html += '</div>';
    }
    html += '<div class="vm-picker-group"><div class="vm-picker-heading">Students</div>';
    students.forEach(function (student) {
      const disabled = student.character_id == null ? ' disabled' : '';
      const note = student.character_id == null ? ' — no character' : '';
      html +=
        '<label class="vm-picker-option' +
        (disabled ? ' vm-picker-disabled' : '') +
        '"><input type="checkbox" data-student-id="' +
        student.id +
        '"' +
        disabled +
        '> ' +
        escapeHtml(student.name) +
        note +
        '</label>';
    });
    html += '</div></div></fieldset>';
    this.root.innerHTML = html;

    const self = this;
    this.root.querySelectorAll('input[name="vm-target"]').forEach(function (radio) {
      radio.addEventListener('change', function () {
        self._syncCustom();
      });
    });
    this._syncCustom();
  };

  VolumeMeterPicker.prototype._syncCustom = function () {
    const custom = this.root.querySelector('input[name="vm-target"][value="custom"]');
    const wrap = this.root.querySelector('.vm-picker-custom');
    if (!wrap) return;
    const on = !!(custom && custom.checked);
    wrap.hidden = !on;
    wrap.querySelectorAll('input[type="checkbox"]').forEach(function (box) {
      if (!box.disabled) box.disabled = false;
      if (!on) {
        /* keep values; just hide */
      }
    });
  };

  VolumeMeterPicker.prototype.getSelection = function () {
    const custom = this.root.querySelector('input[name="vm-target"][value="custom"]');
    if (!custom || !custom.checked) {
      return { target_type: 'class' };
    }
    const clanIds = [];
    const studentIds = [];
    this.root.querySelectorAll('input[data-clan-id]:checked').forEach(function (el) {
      clanIds.push(parseInt(el.getAttribute('data-clan-id'), 10));
    });
    this.root.querySelectorAll('input[data-student-id]:checked').forEach(function (el) {
      if (el.disabled) return;
      studentIds.push(parseInt(el.getAttribute('data-student-id'), 10));
    });
    return { target_type: 'custom', clan_ids: clanIds, student_ids: studentIds };
  };

  VolumeMeterPicker.prototype.setLocked = function (locked) {
    this.root.querySelectorAll('input').forEach(function (el) {
      const noCharacter = el.parentElement && el.parentElement.classList.contains('vm-picker-disabled');
      el.disabled = noCharacter ? true : !!locked;
    });
  };

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  global.VolumeMeterPicker = VolumeMeterPicker;
})(typeof window !== 'undefined' ? window : globalThis);
