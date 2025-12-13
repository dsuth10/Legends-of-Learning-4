// static/js/clans.js
// Teacher Clan Management UI Logic

// Debug logging only in development (remove in production)
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  console.log('[DEBUG] clans.js loaded');
}

document.addEventListener('DOMContentLoaded', function () {
  // DOM elements
  const classSelect = document.getElementById('class-select');
  const clanColumns = document.getElementById('clan-columns');
  const studentRoster = document.getElementById('student-roster');
  const addClanBtn = document.getElementById('add-clan-btn');
  const clanFormModal = new bootstrap.Modal(document.getElementById('clanFormModal'));
  const clanForm = document.getElementById('clan-form');
  const deleteClanModal = new bootstrap.Modal(document.getElementById('deleteClanModal'));
  const confirmDeleteClanBtn = document.getElementById('confirm-delete-clan-btn');
  const clanSpinner = document.getElementById('clan-spinner');
  const clanError = document.getElementById('clan-error');
  const clanSuccess = document.getElementById('clan-success');

  let classes = [];
  let clans = [];
  let students = [];
  let selectedClassId = null;
  let clanToDelete = null;

  // Utility functions
  function showSpinner(show) {
    clanSpinner.classList.toggle('d-none', !show);
  }
  function showError(msg) {
    clanError.textContent = msg;
    clanError.classList.remove('d-none');
    setTimeout(() => clanError.classList.add('d-none'), 5000);
  }
  function showSuccess(msg) {
    clanSuccess.textContent = msg;
    clanSuccess.classList.remove('d-none');
    setTimeout(() => clanSuccess.classList.add('d-none'), 3000);
  }
  function clearRoster() {
    studentRoster.innerHTML = '';
  }
  function clearClans() {
    clanColumns.innerHTML = '';
  }

  // Fetch classes for the teacher
  function fetchClasses() {
    showSpinner(true);
    fetch('/teacher/api/teacher/classes')
      .then(res => res.json())
      .then(data => {
        // Debug logging (development only)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
          console.log('[DEBUG] /teacher/api/teacher/classes response:', data);
        }
        if (!data.success) throw new Error('Failed to load classes.');
        classes = data.classes;
        // Debug logging (development only)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
          console.log('[DEBUG] classes array:', classes);
        }
        populateClassSelect();
        showSpinner(false);
      })
      .catch((err) => {
        // Always log errors, but format appropriately
        console.error('Error fetching classes:', err);
        showError('Failed to load classes.');
        showSpinner(false);
      });
  }

  // Populate class selector
  function populateClassSelect() {
    // Debug logging (development only)
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      console.log('[DEBUG] populateClassSelect called with:', classes);
    }
    classSelect.innerHTML = '';
    if (classes.length === 0) {
      classSelect.innerHTML = '<option>No classes found</option>';
      return;
    }
    classes.forEach(c => {
      // Debug logging (development only)
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('[DEBUG] Adding class to dropdown:', c);
      }
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.name;
      classSelect.appendChild(opt);
    });
    selectedClassId = classes[0].id;
    classSelect.value = selectedClassId;
    fetchClansAndStudents();
  }

  // Fetch clans and students for the selected class
  function fetchClansAndStudents() {
    if (!selectedClassId) return;
    showSpinner(true);
    Promise.all([
      fetch(`/teacher/api/teacher/clans?class_id=${selectedClassId}`).then(r => r.json()),
      fetch(`/teacher/api/teacher/class/${selectedClassId}/students`).then(r => r.json())
    ]).then(([clanRes, studentRes]) => {
      if (!clanRes.success) throw new Error(clanRes.message);
      if (!studentRes.success) throw new Error(studentRes.message);
      clans = clanRes.clans;
      students = studentRes.students;
      renderClans();
      renderStudentRoster();
      showSpinner(false);
    }).catch(e => {
      showError(e.message || 'Failed to load clans or students.');
      showSpinner(false);
    });
  }

  // Render student roster (students not in any clan)
  function renderStudentRoster() {
    clearRoster();
    let unassigned = [];
    students.forEach(s => {
      s.characters.forEach(c => {
        if (!c.clan_id) {
          unassigned.push({
            student: s,
            character: c
          });
        }
      });
    });
    if (unassigned.length === 0) {
      studentRoster.innerHTML = '<li class="list-group-item text-muted">No unassigned students</li>';
      return;
    }
    unassigned.forEach(({ student, character }) => {
      const li = document.createElement('li');
      li.className = 'list-group-item d-flex align-items-center draggable-student';
      li.draggable = true;
      li.dataset.characterId = character.id;
      li.innerHTML = `<img src="${character.avatar_url || '/static/avatars/default.png'}" class="rounded me-2" width="32" height="32" alt="avatar"> <span>${student.username} (${character.name})</span>`;
      li.addEventListener('dragstart', handleStudentDragStart);
      studentRoster.appendChild(li);
    });
  }

  // Render clan columns
  function renderClans() {
    clearClans();
    if (clans.length === 0) {
      clanColumns.innerHTML = '<div class="col"><div class="alert alert-info">No clans found. Add a clan to get started.</div></div>';
      return;
    }
    clans.forEach(clan => {
      const col = document.createElement('div');
      col.className = 'col-md-4 mb-3';
      col.innerHTML = `
        <div class="card clan-card" data-clan-id="${clan.id}">
          <div class="card-header d-flex justify-content-between align-items-center">
            <span><img src="${clan.emblem || '/static/avatars/default.png'}" width="32" height="32" class="me-2"> <strong>${clan.name}</strong></span>
            <div class="d-flex flex-wrap gap-1 mt-1">
              ${(clan.badges || []).map(b => `<img src='${b.icon}' title='${b.name}: ${b.description}' alt='${b.name}' style='width:28px;height:28px;' class='badge-icon'>`).join('')}
            </div>
            <span>
              <button class="btn btn-sm btn-outline-success ms-2 award-badge-btn" data-clan-id="${clan.id}"><i class="fas fa-medal"></i> Award Badge</button>
              <button class="btn btn-sm btn-outline-secondary edit-clan-btn" data-clan-id="${clan.id}"><i class="fas fa-edit"></i></button>
              <button class="btn btn-sm btn-outline-danger delete-clan-btn" data-clan-id="${clan.id}"><i class="fas fa-trash"></i></button>
            </span>
          </div>
          <div class="card-body clan-dropzone" data-clan-id="${clan.id}" style="min-height: 120px;">
            <ul class="list-group mb-2 clan-member-list" id="clan-members-${clan.id}">
              ${clan.members.map(m => `
                <li class="list-group-item d-flex align-items-center draggable-student" draggable="true" data-character-id="${m.id}">
                  <img src="${m.avatar_url || '/static/avatars/default.png'}" class="rounded me-2" width="32" height="32" alt="avatar">
                  <span>${m.name}</span>
                  <button class="btn btn-sm btn-outline-danger ms-auto remove-member-btn" data-character-id="${m.id}" data-clan-id="${clan.id}"><i class="fas fa-times"></i></button>
                </li>
              `).join('')}
            </ul>
          </div>
        </div>
      `;
      // Drag-and-drop events
      const dropzone = col.querySelector('.clan-dropzone');
      dropzone.addEventListener('dragover', handleClanDragOver);
      dropzone.addEventListener('drop', handleClanDrop);
      // Edit/delete buttons
      col.querySelector('.edit-clan-btn').addEventListener('click', () => openClanForm(clan));
      col.querySelector('.delete-clan-btn').addEventListener('click', () => confirmDeleteClan(clan));
      // Remove member buttons
      col.querySelectorAll('.remove-member-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          removeMemberFromClan(btn.dataset.clanId, btn.dataset.characterId);
        });
      });
      // Make clan members draggable
      col.querySelectorAll('.draggable-student').forEach(li => {
        li.addEventListener('dragstart', handleStudentDragStart);
      });
      // Award badge button
      col.querySelector('.award-badge-btn').addEventListener('click', () => openAwardBadgeModal(clan.id));
      clanColumns.appendChild(col);
    });
  }

  // Drag-and-drop handlers
  let draggedCharacterId = null;
  let draggedFromClanId = null;
  function handleStudentDragStart(e) {
    draggedCharacterId = e.target.dataset.characterId;
    draggedFromClanId = e.target.closest('.clan-card')?.dataset.clanId || null;
    e.dataTransfer.effectAllowed = 'move';
  }
  function handleClanDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }
  function handleClanDrop(e) {
    e.preventDefault();
    const targetClanId = e.currentTarget.dataset.clanId;
    if (draggedCharacterId && targetClanId) {
      if (draggedFromClanId && draggedFromClanId !== targetClanId) {
        // Move character from one clan to another: remove from old, then add to new
        showSpinner(true);
        removeMemberFromClan(draggedFromClanId, draggedCharacterId)
          .then(() => addMemberToClan(targetClanId, draggedCharacterId))
          .finally(() => {
            showSpinner(false);
            draggedCharacterId = null;
            draggedFromClanId = null;
          });
      } else {
        // Add unassigned character to clan
        addMemberToClan(targetClanId, draggedCharacterId);
        draggedCharacterId = null;
        draggedFromClanId = null;
      }
    }
  }

  // Add member to clan
  function addMemberToClan(clanId, characterId) {
    showSpinner(true);
    fetch(`/teacher/api/teacher/clans/${clanId}/add_member`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: characterId })
    })
      .then(r => r.json())
      .then(res => {
        if (!res.success) throw new Error(res.message);
        showSuccess('Student assigned to clan.');
        fetchClansAndStudents();
      })
      .catch(e => showError(e.message || 'Failed to assign student.'))
      .finally(() => showSpinner(false));
  }

  // Remove member from clan
  function removeMemberFromClan(clanId, characterId) {
    showSpinner(true);
    return fetch(`/teacher/api/teacher/clans/${clanId}/remove_member`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: characterId })
    })
      .then(r => r.json())
      .then(res => {
        if (!res.success) throw new Error(res.message);
        showSuccess('Student removed from clan.');
        fetchClansAndStudents();
      })
      .catch(e => showError(e.message || 'Failed to remove student.'))
      .finally(() => showSpinner(false));
  }

  // Icon picker logic
  function loadClanIcons(selectedIconUrl, usedEmblems = [], currentClanEmblem = null) {
    const picker = document.getElementById('clan-icon-picker');
    const preview = document.getElementById('clan-icon-preview');
    const hiddenInput = document.getElementById('clan-emblem');
    picker.innerHTML = '';
    preview.innerHTML = '';
    fetch('/teacher/api/teacher/clan-icons')
      .then(res => res.json())
      .then(data => {
        if (!data.success) throw new Error('Failed to load clan icons');
        data.icons.forEach(url => {
          const img = document.createElement('img');
          img.src = url;
          img.className = 'clan-icon-option rounded border';
          img.style.width = '48px';
          img.style.height = '48px';
          img.style.cursor = 'pointer';
          img.style.objectFit = 'cover';
          // Disable if used by another clan (not the current clan)
          const isUsed = usedEmblems.includes(url) && url !== currentClanEmblem;
          if (isUsed) {
            img.classList.add('opacity-50');
            img.style.pointerEvents = 'none';
            img.title = 'Already used by another clan in this class';
          } else {
            img.onclick = () => {
              document.querySelectorAll('.clan-icon-option').forEach(i => i.classList.remove('border-primary'));
              img.classList.add('border-primary');
              hiddenInput.value = url;
              preview.innerHTML = `<img src='${url}' width='48' height='48' class='rounded border border-primary' />`;
            };
          }
          if (selectedIconUrl && url === selectedIconUrl) {
            img.classList.add('border-primary');
            hiddenInput.value = url;
            preview.innerHTML = `<img src='${url}' width='48' height='48' class='rounded border border-primary' />`;
          }
          picker.appendChild(img);
        });
      })
      .catch(() => {
        picker.innerHTML = '<span class="text-danger">Failed to load icons</span>';
      });
  }

  // Banner picker logic
  function loadClanBanners(selectedBannerUrl) {
    const picker = document.getElementById('clan-banner-picker');
    const preview = document.getElementById('clan-banner-preview');
    const hiddenInput = document.getElementById('clan-banner');
    picker.innerHTML = '';
    preview.innerHTML = '';
    // Hardcoded banners for now; in production, fetch from server or scan directory
    const banners = [
      '/static/images/clan_banners/banner1.png',
      '/static/images/clan_banners/banner2.png',
      '/static/images/clan_banners/banner3.png',
      '/static/images/clan_banners/banner4.png',
      '/static/images/clan_banners/banner5.png'
    ];
    banners.forEach(url => {
      const img = document.createElement('img');
      img.src = url;
      img.className = 'clan-banner-option rounded border';
      img.style.width = '96px';
      img.style.height = '32px';
      img.style.cursor = 'pointer';
      img.style.objectFit = 'cover';
      img.onclick = () => {
        document.querySelectorAll('.clan-banner-option').forEach(i => i.classList.remove('border-primary'));
        img.classList.add('border-primary');
        hiddenInput.value = url;
        preview.innerHTML = `<img src='${url}' width='192' height='64' class='rounded border border-primary' />`;
      };
      if (selectedBannerUrl && url === selectedBannerUrl) {
        img.classList.add('border-primary');
        hiddenInput.value = url;
        preview.innerHTML = `<img src='${url}' width='192' height='64' class='rounded border border-primary' />`;
      }
      picker.appendChild(img);
    });
  }

  // Open clan form modal for create/edit
  function openClanForm(clan) {
    document.getElementById('clan-id').value = clan ? clan.id : '';
    document.getElementById('clan-name').value = clan ? clan.name : '';
    document.getElementById('clan-description').value = clan ? clan.description || '' : '';
    // Gather used emblems (excluding current clan's emblem)
    const currentClanEmblem = clan ? clan.emblem || '' : '';
    const usedEmblems = clans
      .filter(c => c.emblem && (!clan || c.id !== clan.id))
      .map(c => c.emblem);
    loadClanIcons(currentClanEmblem, usedEmblems, currentClanEmblem);
    loadClanBanners(clan ? clan.banner || '' : '');
    document.getElementById('clan-banner').value = clan ? clan.banner || '' : '';
    document.getElementById('clan-theme-color').value = clan ? clan.theme_color || '#2470dc' : '#2470dc';
    clanFormModal.show();
  }

  // Handle clan form submit
  clanForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const clanId = document.getElementById('clan-id').value;
    const name = document.getElementById('clan-name').value.trim();
    const description = document.getElementById('clan-description').value.trim();
    const emblem = document.getElementById('clan-emblem').value.trim();
    const banner = document.getElementById('clan-banner').value.trim();
    const theme_color = document.getElementById('clan-theme-color').value.trim();
    if (!name) {
      showError('Clan name is required.');
      return;
    }
    showSpinner(true);
    const method = clanId ? 'PUT' : 'POST';
    const url = clanId ? `/teacher/api/teacher/clans/${clanId}` : '/teacher/api/teacher/clans';
    const payload = {
      name,
      description,
      emblem,
      banner,
      theme_color,
      class_id: selectedClassId
    };
    fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(r => r.json())
      .then(res => {
        if (!res.success) throw new Error(res.message);
        showSuccess(clanId ? 'Clan updated.' : 'Clan created.');
        clanFormModal.hide();
        fetchClansAndStudents();
      })
      .catch(e => showError(e.message || 'Failed to save clan.'))
      .finally(() => showSpinner(false));
  });

  // Add clan button
  addClanBtn.addEventListener('click', () => openClanForm(null));

  // Delete clan
  function confirmDeleteClan(clan) {
    clanToDelete = clan;
    deleteClanModal.show();
  }
  confirmDeleteClanBtn.addEventListener('click', function () {
    if (!clanToDelete) return;
    showSpinner(true);
    fetch(`/teacher/api/teacher/clans/${clanToDelete.id}`, {
      method: 'DELETE'
    })
      .then(r => r.json())
      .then(res => {
        if (!res.success) throw new Error(res.message);
        showSuccess('Clan deleted.');
        deleteClanModal.hide();
        fetchClansAndStudents();
      })
      .catch(e => showError(e.message || 'Failed to delete clan.'))
      .finally(() => {
        showSpinner(false);
        clanToDelete = null;
      });
  });

  // Class selector change
  classSelect.addEventListener('change', function () {
    selectedClassId = classSelect.value;
    fetchClansAndStudents();
  });

  // Award Badge Modal logic
  const awardBadgeModal = new bootstrap.Modal(document.getElementById('awardBadgeModal'));
  const badgeList = document.getElementById('badge-list');
  const awardBadgeBtn = document.getElementById('award-badge-btn');
  const badgeAwardError = document.getElementById('badge-award-error');
  let selectedBadgeId = null;
  let awardBadgeClanId = null;

  function openAwardBadgeModal(clanId) {
    awardBadgeClanId = clanId;
    selectedBadgeId = null;
    awardBadgeBtn.disabled = true;
    badgeAwardError.classList.add('d-none');
    badgeList.innerHTML = '<div>Loading badges...</div>';
    fetch('/teacher/api/badges')
      .then(res => res.json())
      .then(data => {
        if (!data.success) throw new Error('Failed to load badges');
        badgeList.innerHTML = '';
        data.badges.filter(b => b.is_clan).forEach(badge => {
          const img = document.createElement('img');
          img.src = badge.icon;
          img.title = badge.name + ': ' + badge.description;
          img.alt = badge.name;
          img.style.width = '48px';
          img.style.height = '48px';
          img.className = 'badge-icon border rounded m-1';
          img.style.cursor = 'pointer';
          img.onclick = () => {
            document.querySelectorAll('#badge-list .badge-icon').forEach(i => i.classList.remove('border-primary'));
            img.classList.add('border-primary');
            selectedBadgeId = badge.id;
            awardBadgeBtn.disabled = false;
          };
          badgeList.appendChild(img);
        });
      })
      .catch(() => {
        badgeList.innerHTML = '<span class="text-danger">Failed to load badges</span>';
      });
    awardBadgeModal.show();
  }

  awardBadgeBtn.addEventListener('click', function() {
    if (!selectedBadgeId || !awardBadgeClanId) return;
    awardBadgeBtn.disabled = true;
    badgeAwardError.classList.add('d-none');
    fetch(`/teacher/api/clans/${awardBadgeClanId}/badges`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ badge_id: selectedBadgeId })
    })
      .then(r => r.json())
      .then(res => {
        if (!res.success) throw new Error(res.message);
        awardBadgeModal.hide();
        showSuccess('Badge awarded!');
        fetchClansAndStudents();
      })
      .catch(e => {
        badgeAwardError.textContent = e.message || 'Failed to award badge.';
        badgeAwardError.classList.remove('d-none');
        awardBadgeBtn.disabled = false;
      });
  });

  // Initial load
  fetchClasses();
}); 